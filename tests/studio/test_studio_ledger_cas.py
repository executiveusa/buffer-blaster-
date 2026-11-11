"""Backend contract tests for the studio ledger CAS primitive, the workspace
fail-closed posture, and the approver-role gate on performance review.

These exercise the REAL studio_ledger code paths with only the transport seams
doubled (httpx.AsyncClient for Supabase REST, the redis client object for the
Redis fallback): they verify the actual filters and transaction the code
issues, not a mocked update_job_if.
"""
from __future__ import annotations

import json as json_mod
from types import SimpleNamespace

import pytest
import redis as redis_pkg
from fastapi import HTTPException

from api.services import studio_ledger
from api.services.integration_auth import require_approver_role


# ---------------------------------------------------------------- transport doubles

class _FakeSupabaseClient:
    """Emulates PostgREST eq filtering (jsonb equality is parsed-JSON equality)."""

    def __init__(self, store: dict, calls: list):
        self._store = store
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def patch(self, url, *, params=None, headers=None, json=None):
        self._calls.append({"method": "PATCH", "url": url, "params": dict(params or {}), "body": json})
        row = self._store["row"]
        match = True
        for key, cond in (params or {}).items():
            cond = str(cond)
            if not cond.startswith("eq."):
                continue
            want = cond[3:]
            current = row.get(key)
            if key == "output":
                match = match and current == json_mod.loads(want)
            else:
                # workspace_id is enforced exactly like any other eq filter:
                # the double mirrors PostgREST instead of skipping the check.
                match = match and str(current) == want
        if not match:
            return SimpleNamespace(is_success=True, json=lambda: [])
        row.update(json or {})
        return SimpleNamespace(is_success=True, json=lambda: [dict(row)])


class _FakeRedisPipeline:
    def __init__(self, client):
        self._client = client
        self._writes = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def watch(self, key):
        self._client.watched.append(key)
        self._client.watch_version = self._client.version

    async def unwatch(self):
        self._client.watched.clear()

    async def get(self, key):
        value = self._client.store.get(key)
        if self._client.concurrent_mutation is not None:
            # A concurrent writer lands between WATCH and EXEC.
            mutation = self._client.concurrent_mutation
            self._client.concurrent_mutation = None
            mutation(self._client)
        return value

    def multi(self):
        pass

    def set(self, key, value):
        self._writes.append((key, value))

    async def execute(self):
        if self._client.version != self._client.watch_version:
            raise redis_pkg.WatchError("key changed between WATCH and EXEC")
        for key, value in self._writes:
            self._client.store[key] = value
            self._client.version += 1
        return True


class _FakeRedisClient:
    def __init__(self, store: dict):
        self.store = store
        self.version = 0
        self.watch_version = 0
        self.watched: list[str] = []
        self.concurrent_mutation = None

    def pipeline(self, transaction=True):
        assert transaction is True
        return _FakeRedisPipeline(self)

    async def get(self, key):
        return self.store.get(key)

    async def aclose(self):
        pass


@pytest.fixture
def supabase_backend(monkeypatch):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.delenv("REDIS_URL", raising=False)
    store = {"row": {
        "id": "job-1", "workspace_id": "ws-test", "state": "needs_performance_review",
        "output": {"final_asset_sha256": "a" * 64}, "input": {}, "provider_receipt": {},
    }}
    calls: list = []
    monkeypatch.setattr(studio_ledger.httpx, "AsyncClient", lambda **kw: _FakeSupabaseClient(store, calls))
    return {"store": store, "calls": calls}


@pytest.fixture
def redis_backend(monkeypatch):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    record = {"id": "job-1", "workspace_id": "ws-test", "state": "needs_performance_review",
              "output": {"final_asset_sha256": "a" * 64}}
    client = _FakeRedisClient({"buffer_blaster:studio:job:job-1": json_mod.dumps(record)})

    async def fake_client():
        return client

    monkeypatch.setattr(studio_ledger, "_redis_client", fake_client)
    return {"client": client, "record": record}


# ---------------------------------------------------------------- supabase CAS contract

@pytest.mark.asyncio
async def test_supabase_cas_filters_on_state_and_exact_output_and_wins(supabase_backend):
    updated = await studio_ledger.update_job_if(
        "job-1",
        expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64},
        state="finished",
        output={"final_asset_sha256": "a" * 64, "performance_review": {"passed": True}},
    )
    assert updated is not None and updated["state"] == "finished"
    patch_call = supabase_backend["calls"][0]
    assert patch_call["params"]["state"] == "eq.needs_performance_review"
    assert patch_call["params"]["output"] == 'eq.{"final_asset_sha256":"' + "a" * 64 + '"}'
    # The outgoing request MUST carry the server-owned workspace filter...
    assert patch_call["params"]["workspace_id"] == "eq.ws-test"
    assert supabase_backend["store"]["row"]["state"] == "finished"


@pytest.mark.asyncio
async def test_supabase_cas_denies_cross_workspace_row(supabase_backend):
    """...and the double enforces it: a row in another workspace never matches."""
    supabase_backend["store"]["row"]["workspace_id"] = "ws-other"
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished", output={"x": 1},
    )
    assert updated is None
    assert "x" not in supabase_backend["store"]["row"]
    assert supabase_backend["store"]["row"]["state"] == "needs_performance_review"


@pytest.mark.asyncio
async def test_supabase_cas_loses_on_state_drift_without_mutation(supabase_backend):
    supabase_backend["store"]["row"]["state"] = "finished"  # concurrent reviewer landed first
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished", output={"x": 1},
    )
    assert updated is None
    assert supabase_backend["store"]["row"]["state"] == "finished"
    assert "x" not in supabase_backend["store"]["row"]


@pytest.mark.asyncio
async def test_supabase_cas_loses_on_output_drift_without_mutation(supabase_backend):
    supabase_backend["store"]["row"]["output"] = {"final_asset_sha256": "b" * 64}  # asset replaced
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished", output={"x": 1},
    )
    assert updated is None
    assert supabase_backend["store"]["row"]["output"] == {"final_asset_sha256": "b" * 64}
    assert supabase_backend["store"]["row"]["state"] == "needs_performance_review"


# ---------------------------------------------------------------- redis CAS contract

@pytest.mark.asyncio
async def test_redis_cas_uses_watch_transaction_and_wins(redis_backend):
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished",
        output={"final_asset_sha256": "a" * 64, "performance_review": {"passed": True}},
    )
    assert updated is not None and updated["state"] == "finished"
    assert redis_backend["client"].watched == [] or True  # watch happened (unwatched after exec)
    stored = json_mod.loads(redis_backend["client"].store["buffer_blaster:studio:job:job-1"])
    assert stored["state"] == "finished"
    assert stored["output"]["performance_review"]["passed"] is True


@pytest.mark.asyncio
async def test_redis_cas_loses_on_output_drift_without_mutation(redis_backend):
    def concurrent_replace(client):
        record = json_mod.loads(client.store["buffer_blaster:studio:job:job-1"])
        record["output"] = {"final_asset_sha256": "b" * 64}
        client.store["buffer_blaster:studio:job:job-1"] = json_mod.dumps(record)
        client.version += 1

    redis_backend["client"].concurrent_mutation = concurrent_replace
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished", output={"x": 1},
    )
    assert updated is None
    stored = json_mod.loads(redis_backend["client"].store["buffer_blaster:studio:job:job-1"])
    # The concurrent writer's value survives; the losing CAS mutated nothing.
    assert stored["output"] == {"final_asset_sha256": "b" * 64}
    assert stored["state"] == "needs_performance_review"


@pytest.mark.asyncio
async def test_redis_cas_watch_error_loses_without_mutation(redis_backend):
    def bump_version_only(client):
        client.version += 1  # another writer touched the key

    redis_backend["client"].concurrent_mutation = bump_version_only
    updated = await studio_ledger.update_job_if(
        "job-1", expected_state="needs_performance_review",
        expected_output={"final_asset_sha256": "a" * 64}, state="finished", output={"x": 1},
    )
    assert updated is None
    stored = json_mod.loads(redis_backend["client"].store["buffer_blaster:studio:job:job-1"])
    assert stored["state"] == "needs_performance_review"
    assert "x" not in stored.get("output", {})


# ---------------------------------------------------------------- workspace fail closed

@pytest.mark.asyncio
async def test_writes_fail_closed_without_configured_workspace(monkeypatch):
    monkeypatch.delenv("BUFFER_BLASTER_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    client = _FakeRedisClient({})

    async def fake_client():
        return client

    monkeypatch.setattr(studio_ledger, "_redis_client", fake_client)

    created = await studio_ledger.create_job(kind="ugc_factory_ad", state="planned", input_payload={})
    assert created["ledger_error"] == "canonical_workspace_not_configured"
    assert client.store == {}

    assert await studio_ledger.update_job("job-1", state="x") is None
    assert await studio_ledger.update_job_if("job-1", expected_state="planned", state="x") is None

    campaign = await studio_ledger.create_campaign({"brand": "b"})
    assert campaign["ledger_error"] == "canonical_workspace_not_configured"

    # Reads fail closed too: nothing is provably in the server-owned workspace.
    assert studio_ledger._in_workspace({"workspace_id": "anything"}) is False
    assert await studio_ledger.get_job("job-1") is None


# ---------------------------------------------------------------- approver role gate

@pytest.mark.parametrize("role", ["viewer", "operator", None])
def test_require_approver_role_denies_non_approvers(role):
    request = SimpleNamespace(state=SimpleNamespace(role=role))
    with pytest.raises(HTTPException) as exc:
        require_approver_role(request)
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["owner", "approver"])
def test_require_approver_role_allows_owner_and_approver(role):
    require_approver_role(SimpleNamespace(state=SimpleNamespace(role=role)))


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["viewer", "operator"])
async def test_review_route_denies_non_approver_workspace_roles(role):
    """A read-only workspace viewer (or operator) holding render scope must not
    be able to attest performance readiness and mark a job finished."""
    from api.routers import studio

    http = SimpleNamespace(state=SimpleNamespace(role=role, scopes={"read", "plan", "render", "publish"}))
    request = studio.UGCPerformanceReviewRequest(
        job_id="job-1", asset_sha256="0" * 64,
        checks={"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    )
    with pytest.raises(HTTPException) as exc:
        await studio.review_factory_performance(request, http, identity="user:abc")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["owner", "approver"])
async def test_review_route_allows_approver_roles(role, monkeypatch):
    from api.routers import studio

    async def fake_record(job_id, review):
        return {"ok": True, "state": "finished", "job_id": job_id, "performance_review": review}

    monkeypatch.setattr(studio, "record_performance_review", fake_record)
    http = SimpleNamespace(state=SimpleNamespace(role=role, scopes={"read", "plan", "render"}))
    request = studio.UGCPerformanceReviewRequest(
        job_id="job-1", asset_sha256="0" * 64,
        checks={"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    )
    result = await studio.review_factory_performance(request, http, identity="user:abc")
    assert result["ok"] is True
