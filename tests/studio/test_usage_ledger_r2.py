"""S4 r2: reviewer money-boundary fixes - write-time cap validation, fail-closed
reads, atomic check+hold (no TOCTOU), cost_unknown rejection, mirror backlog
fail-closed + provable reconcile, owner-only caps, CSV safety, LLM wiring."""
from __future__ import annotations

import asyncio

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services import llm_adapter, model_settings, runtime_settings, usage_ledger
from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary


@pytest.fixture
def redis_fake(monkeypatch):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(usage_ledger.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(model_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(runtime_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    for k in usage_ledger._CAP_KEYS:
        monkeypatch.delenv(k, raising=False)
    return fake


# ------------------------------------------------------------ cap validation


@pytest.mark.asyncio
async def test_cap_write_rejects_non_integer_and_negative(redis_fake):
    bad = await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "abc")
    assert bad["ok"] is False and bad["error"] == "invalid_cap_value"
    neg = await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "-5")
    assert neg["ok"] is False and neg["error"] == "invalid_cap_value"
    good = await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "150")
    assert good["ok"] is True
    assert await runtime_settings.get_value("USAGE_CAP_DAILY_CENTS") == "150"


@pytest.mark.asyncio
async def test_invalid_stored_cap_fails_closed_not_disabled(redis_fake):
    # Written directly, bypassing set_value validation (legacy/bad data).
    await redis_fake.hset(runtime_settings._HASH_KEY, "USAGE_CAP_DAILY_CENTS", "-1")
    res = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=1)
    assert res["ok"] is False and res["error"] == "cap_config_invalid"
    assert res["invalid_keys"] == ["USAGE_CAP_DAILY_CENTS"]


# ------------------------------------------------------------ atomic hold


@pytest.mark.asyncio
async def test_estimate_required_before_execution(redis_fake):
    res = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=None)
    assert res["ok"] is False and res["error"] == "estimate_required"


@pytest.mark.asyncio
async def test_concurrent_holds_cannot_jointly_exceed_cap(redis_fake):
    """TOCTOU: three concurrent 60c holds against a 100c cap. At most one may
    be admitted, and every rejected hold must roll back cleanly."""
    import time as _time
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100")
    results = await asyncio.gather(
        usage_ledger.check_and_hold(job_id="j1", estimated_cents=60),
        usage_ledger.check_and_hold(job_id="j2", estimated_cents=60),
        usage_ledger.check_and_hold(job_id="j3", estimated_cents=60),
    )
    admitted = [r for r in results if r.get("ok")]
    blocked = [r for r in results if not r.get("ok")]
    assert len(admitted) <= 1, "concurrent runs jointly exceeded the cap"
    assert all(b["error"] == "workspace_cap_exceeded" and b["window"] == "day" for b in blocked)
    day = _time.strftime("%Y-%m-%d", _time.gmtime())
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    assert int(totals.get(f"held:day:{day}", 0)) == 60 * len(admitted), "rejected holds leaked"


@pytest.mark.asyncio
async def test_sequential_hold_block_release_hold(redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100")
    first = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=60)
    assert first["ok"] is True
    second = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=60)
    assert second["ok"] is False and second["error"] == "workspace_cap_exceeded"
    await usage_ledger.release_hold(first["hold"])
    third = await usage_ledger.check_and_hold(job_id="j3", estimated_cents=60)
    assert third["ok"] is True, "released hold must free cap room"


@pytest.mark.asyncio
async def test_hold_settles_into_spent_and_releases_remainder(redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100")
    hold = (await usage_ledger.check_and_hold(job_id="j1", estimated_cents=80))["hold"]
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="j1", estimated_cents=50)
    await usage_ledger.release_hold(hold)
    day_field = "held:day:" + hold["windows"]["day"]
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    assert int(totals.get(day_field, 0)) == 0
    assert int(totals["spent:day:" + hold["windows"]["day"]]) == 50
    # after settle, a 60c hold against the 100c cap fits (50 spent)
    again = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=49)
    assert again["ok"] is True
    over = await usage_ledger.check_and_hold(job_id="j3", estimated_cents=51)
    assert over["ok"] is False and over["error"] == "workspace_cap_exceeded"


@pytest.mark.asyncio
async def test_record_usage_rejects_unknown_cost(redis_fake):
    res = await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="llm",
                                          tokens_in=10, tokens_out=5)
    assert res["ok"] is False and res["error"] == "cost_unknown"
    assert await usage_ledger.list_events() == []


# ------------------------------------------------------------ mirror durability


class _FakeResp:
    def __init__(self, status_code=200, body=None, headers=None):
        self.status_code = status_code
        self._body = body if body is not None else []
        self.headers = headers or {}

    def json(self):
        return self._body


class _FakeHTTP:
    """Scriptable PostgREST double. fails controls write status.
    GET honors Range-Unit/Range and answers with an exact Content-Range,
    like PostgREST with Prefer: count=exact."""

    def __init__(self):
        self.calls = []
        self.write_status = 201
        self.rows = []

    async def __call__(self, method, url, **kwargs):
        self.calls.append((method, url))
        if method == "POST":
            if self.write_status < 300:
                self.rows.append(kwargs["json"])
            return _FakeResp(self.write_status)
        headers = kwargs.get("headers") or {}
        rng = headers.get("Range", "0-999")
        try:
            start, end = (int(p) for p in rng.split("-", 1))
        except ValueError:
            start, end = 0, 999
        page = self.rows[start:end + 1]
        return _FakeResp(200, page,
                         headers={"content-range": f"{start}-{start + max(len(page) - 1, 0)}/{len(self.rows)}"})


@pytest.fixture
def mirror_env(monkeypatch, redis_fake):
    """PostgREST double injected into every mirror call (record + reconcile)."""
    http = _FakeHTTP()
    monkeypatch.setenv("SUPABASE_URL", "https://supa.test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc-key")
    orig = usage_ledger._mirror_usage_event

    async def patched(event, *, http=None):
        return await orig(event, http=http or patched.fake)
    patched.fake = http
    monkeypatch.setattr(usage_ledger, "_mirror_usage_event", patched)
    orig_reconcile = usage_ledger.reconcile_mirror

    async def reconcile_wrapped(**kw):
        kw.setdefault("http", http)
        return await orig_reconcile(**kw)
    monkeypatch.setattr(usage_ledger, "reconcile_mirror", reconcile_wrapped)
    return http


@pytest.mark.asyncio
async def test_mirror_500_backlogs_and_hold_fails_closed(mirror_env):
    mirror_env.write_status = 500
    res = await usage_ledger.record_usage(actor="a", provider="p", model="m",
                                          kind="video", estimated_cents=10)
    assert res["ok"] is True and res["mirror"] == "backlogged"
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "1000")
    hold = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=5)
    assert hold["ok"] is False and hold["error"] == "ledger_mirror_backlog"


@pytest.mark.asyncio
async def test_reconcile_replays_backlog_and_recovers(mirror_env):
    mirror_env.write_status = 500
    await usage_ledger.record_usage(actor="a", provider="p", model="m",
                                    kind="video", estimated_cents=10, job_id="j1")
    mirror_env.write_status = 201
    rec = await usage_ledger.reconcile_mirror(http=mirror_env)
    assert rec["ok"] is True and rec["backlog_remaining"] == 0 and rec["rows_reconciled"] == 1
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "1000")
    hold = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=5)
    assert hold["ok"] is True


@pytest.mark.asyncio
async def test_redis_reset_rebuilds_totals_from_mirror(mirror_env, redis_fake):
    # a recorded, mirrored event
    await usage_ledger.record_usage(actor="a", provider="p", model="m",
                                    kind="video", estimated_cents=70, job_id="j1")
    assert mirror_env.rows, "event should have mirrored to the durable store"
    # simulate Redis reset: wipe everything, keep only env
    await redis_fake.flushall()
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100")
    # hold triggers inline reconcile from the durable mirror: 70 spent + 40 > 100
    blocked = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=40)
    assert blocked["ok"] is False and blocked["error"] == "workspace_cap_exceeded"


# ------------------------------------------------------------ model settings


@pytest.mark.asyncio
async def test_workspace_reasoning_level_validated_at_write(redis_fake):
    bad = await runtime_settings.set_value("MODEL_REASONING_LEVEL", "gigabrain")
    assert bad["ok"] is False and bad["error"] == "invalid_reasoning_level"
    good = await runtime_settings.set_value("MODEL_REASONING_LEVEL", "high")
    assert good["ok"] is True


@pytest.mark.asyncio
async def test_step_config_is_workspace_isolated(redis_fake, monkeypatch):
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-a")
    await model_settings.set_step_config("script", reasoning_level="high")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-b")
    assert await model_settings._step_config("script") == {}
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-a")
    assert (await model_settings._step_config("script"))["reasoning_level"] == "high"


@pytest.mark.asyncio
async def test_invalid_stored_step_level_rejected_at_resolve(redis_fake):
    await redis_fake.hset(model_settings._step_key("script"), mapping={"reasoning_level": "gigabrain"})
    res = await model_settings.resolve_model_config(step="script")
    assert res["ok"] is False and res["error"] == "invalid_reasoning_level"


# ------------------------------------------------------------ settings route


@pytest.fixture
def admin_client(monkeypatch, redis_fake):
    import api.deps as deps

    async def fake_member(request, token):
        request.state.role = fake_member.role
        return "user:00000000-0000-0000-0000-000000000001"
    fake_member.role = "operator"
    monkeypatch.setattr(deps, "authenticate_member", fake_member)
    patch_journey_boundary()
    client = TestClient(app)
    headers = {"Authorization": "Bearer aaa.bbb.ccc"}
    return client, headers, fake_member


def test_caps_are_owner_only_not_operator(admin_client):
    client, headers, member = admin_client
    denied = client.put("/api/admin/settings", json={"env": "USAGE_CAP_DAILY_CENTS", "value": "100"}, headers=headers)
    assert denied.status_code == 403
    member.role = "owner"
    allowed = client.put("/api/admin/settings", json={"env": "USAGE_CAP_DAILY_CENTS", "value": "100"}, headers=headers)
    assert allowed.status_code == 200, allowed.text
    member.role = "operator"
    other = client.put("/api/admin/settings", json={"env": "AGENT_MAX_CHILDREN", "value": "3"}, headers=headers)
    assert other.status_code == 200  # non-cap settings stay operator-editable


def test_stale_409_message_lists_current_editable_keys(admin_client):
    client, headers, _ = admin_client
    resp = client.put("/api/admin/settings", json={"env": "STRIPE_SECRET_KEY", "value": "x"}, headers=headers)
    assert resp.status_code == 409
    assert "USAGE_CAP_DAILY_CENTS" in resp.text and "MODEL_REASONING_LEVEL" in resp.text


# ------------------------------------------------------------ CSV safety


def test_usage_csv_is_formula_safe(monkeypatch, redis_fake):
    import api.routers.usage as usage_router

    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    patch_journey_boundary()

    async def fake_report(group_by="day"):
        return {"ok": True, "rows": [
            {"group": "=HYPERLINK(\"http://evil\")", "events": 1, "estimated_cents": 5,
             "actual_cents": 0, "actual_reported_events": 0,
             "tokens_in": 0, "tokens_out": 0, "wallet_credits": 0}]}
    monkeypatch.setattr(usage_router.usage_ledger, "usage_report", fake_report)
    client = TestClient(app)
    resp = client.get("/api/studio/usage?format=csv",
                      headers={"Authorization": f"Bearer {TEST_OPERATOR_KEY}"})
    assert resp.status_code == 200
    assert "'=HYPERLINK" in resp.text


# ------------------------------------------------------------ LLM wiring


class _LLMResp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


class _LLMClient:
    def __init__(self, body):
        self._body = body
        self.posts = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        self.posts += 1
        return _LLMResp(self._body)


@pytest.fixture
def anthropic_env(monkeypatch, redis_fake):
    monkeypatch.setenv("ACTIVE_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_TEST_IN_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_TEST_OUT_CENTS_PER_MTOK", "1500")
    body = {"content": [{"text": "hello"}],
            "usage": {"input_tokens": 12, "output_tokens": 7}}
    client = _LLMClient(body)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: client)
    return client


@pytest.mark.asyncio
async def test_llm_call_records_one_row_with_real_tokens(anthropic_env):
    text = await llm_adapter.chat("hi", system="s", max_tokens=100)
    assert text == "hello"
    events = await usage_ledger.list_events()
    assert len(events) == 1
    e = events[0]
    assert e["kind"] == "llm" and e["provider"] == "anthropic"
    assert e["tokens_in"] == 12 and e["tokens_out"] == 7
    assert e["estimated_cents"] is not None and e["estimated_cents"] >= 1
    assert e["actual_cents"] is None  # anthropic reports no cost


@pytest.mark.asyncio
async def test_llm_cap_block_happens_before_any_provider_call(anthropic_env):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "1")
    with pytest.raises(llm_adapter.UsageCapExceeded):
        await llm_adapter.chat("x" * 4000, max_tokens=4096)
    assert anthropic_env.posts == 0  # zero provider calls on a blocked spend


@pytest.mark.asyncio
async def test_llm_provider_error_releases_hold_and_records_nothing(anthropic_env, monkeypatch, redis_fake):
    class Boom(_LLMClient):
        async def post(self, *a, **k):
            self.posts += 1
            raise httpx_error()

    def httpx_error():
        import httpx
        return httpx.ConnectError("boom")
    client = Boom({})
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: client)
    with pytest.raises(Exception):
        await llm_adapter.chat("hi", max_tokens=10)
    assert await usage_ledger.list_events() == []
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    assert all(int(v) == 0 for v in totals.values())


def test_llm_estimate_uses_configured_vendor_price(monkeypatch):
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_TEST_IN_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_TEST_OUT_CENTS_PER_MTOK", "1500")
    # r4 bound: 4064 input tokens (4000 bytes + 64 framing overhead) at
    # 300c/Mtok + 4096 output at 1500c/Mtok = 1.2192 + 6.144 -> 8c, exactly
    # the configured vendor price math on the proven byte bound.
    est = llm_adapter.estimate_llm_cents("anthropic", "claude-test", "x" * 4000, "", 4096)
    assert est == -(-(4064 * 300 + 4096 * 1500) // 1_000_000) == 8


@pytest.mark.asyncio
async def test_unconfigured_model_pricing_rejected_before_any_call(anthropic_env, monkeypatch):
    monkeypatch.delenv("LLM_PRICE_ANTHROPIC_CLAUDE_TEST_OUT_CENTS_PER_MTOK")
    with pytest.raises(llm_adapter.ModelPricingUnconfigured) as exc:
        await llm_adapter.chat("hi", max_tokens=10)
    assert exc.value.detail["missing_env"] == ["LLM_PRICE_ANTHROPIC_CLAUDE_TEST_OUT_CENTS_PER_MTOK"]
    assert anthropic_env.posts == 0
