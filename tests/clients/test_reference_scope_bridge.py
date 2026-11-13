"""Cross-workspace source reference read protections for agent-to-agent bridges."""
from __future__ import annotations

from uuid import uuid4
import pytest

from api.services import source_assets

WORKSPACE = str(uuid4())
FOREIGN = str(uuid4())
ASSET = str(uuid4())


class FakeResponse:
    is_success = True
    status_code = 200

    def __init__(self, rows):
        self.rows = rows

    def json(self):
        return self.rows


class FakeClient:
    def __init__(self, responses, log):
        self.responses, self.log = responses, log

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, *, params, headers):
        self.log.append({"url": url, "params": params, "headers": headers})
        return FakeResponse(self.responses)


@pytest.mark.asyncio
async def test_exact_reference_queries_workspace_and_rejects_foreign_rows(monkeypatch):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.setenv("SUPABASE_URL", "https://private-storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "unit-test-key")
    log = []
    rows = [{"id": ASSET, "workspace_id": FOREIGN, "kind": "uploaded_reference"}]
    monkeypatch.setattr(source_assets.httpx, "AsyncClient",
                        lambda **kwargs: FakeClient(rows, log))
    denied = await source_assets.get_reference(ASSET)
    assert denied == {"ok": False, "error": "reference_not_found", "asset": None}
    assert log[0]["params"]["workspace_id"] == f"eq.{WORKSPACE}"
    assert log[0]["params"]["id"] == f"eq.{ASSET}"
    rows[:] = [{"id": ASSET, "workspace_id": WORKSPACE, "kind": "uploaded_reference"}]
    approved = await source_assets.get_reference(ASSET)
    assert approved["ok"] is True
    assert approved["workspace_id"] == WORKSPACE
    assert approved["rights_verified"] is False
    assert approved["paid_generation"] is False


@pytest.mark.asyncio
async def test_list_never_returns_foreign_rows_even_if_backend_does(monkeypatch):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.setenv("SUPABASE_URL", "https://private-storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "unit-test-key")
    log = []
    rows = [
        {"id": ASSET, "workspace_id": WORKSPACE},
        {"id": str(uuid4()), "workspace_id": FOREIGN},
    ]
    monkeypatch.setattr(source_assets.httpx, "AsyncClient",
                        lambda **kwargs: FakeClient(rows, log))
    visible = await source_assets.list_references(20)
    assert len(visible) == 1
    assert visible[0]["workspace_id"] == WORKSPACE
    assert log[0]["params"]["workspace_id"] == f"eq.{WORKSPACE}"


@pytest.mark.asyncio
async def test_reference_read_fails_closed_without_workspace(monkeypatch):
    monkeypatch.delenv("BUFFER_BLASTER_WORKSPACE_ID", raising=False)
    assert (await source_assets.get_reference(ASSET))["error"] == "workspace_not_configured"
    assert await source_assets.list_references(20) == []


@pytest.mark.asyncio
async def test_redis_reference_read_refuses_foreign_workspace(monkeypatch):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/7")

    class FakeRedis:
        async def get(self, key):
            assert key.endswith(ASSET)
            import json
            return json.dumps({"id": ASSET, "workspace_id": FOREIGN})

        async def aclose(self):
            pass

    monkeypatch.setattr(source_assets.redis, "from_url", lambda *args, **kw: FakeRedis())
    result = await source_assets.get_reference(ASSET)
    assert result["ok"] is False
    assert result["error"] == "reference_not_found"


@pytest.mark.asyncio
async def test_redis_listing_scans_past_foreign_workspace_entries(monkeypatch):
    """Global Redis zset may have a full first page of newer foreign records."""
    import json

    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/7")

    foreign_ids = [str(uuid4()) for _ in range(50)]
    owned_id = ASSET
    ordered_ids = foreign_ids + [owned_id]

    class FakeRedis:
        def __init__(self):
            self.pages = []

        async def zrevrange(self, key, start, stop):
            assert key == source_assets._ZSET
            self.pages.append((start, stop))
            return ordered_ids[start:stop + 1]

        async def mget(self, keys):
            result = []
            for key in keys:
                asset_id = key.rsplit(":", 1)[-1]
                is_ours = asset_id == owned_id
                result.append(json.dumps({
                    "id": asset_id,
                    "workspace_id": WORKSPACE if is_ours else FOREIGN,
                }))
            return result

        async def aclose(self):
            pass

    fake = FakeRedis()
    monkeypatch.setattr(source_assets.redis, "from_url", lambda *a, **kw: fake)
    values = await source_assets.list_references(1)
    assert len(values) == 1
    assert values[0]["id"] == ASSET
    assert fake.pages == [(0, 49), (50, 99)]


@pytest.mark.asyncio
async def test_redis_listing_returns_exact_requested_count_after_workspace_filter(monkeypatch):
    import json
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/7")
    target_ids = [str(uuid4()) for _ in range(3)]
    items = [
        {"id": str(uuid4()), "workspace_id": FOREIGN},
        {"id": target_ids[0], "workspace_id": WORKSPACE},
        {"id": str(uuid4()), "workspace_id": FOREIGN},
        {"id": target_ids[1], "workspace_id": WORKSPACE},
        {"id": target_ids[2], "workspace_id": WORKSPACE},
    ]

    class FakeRedis:
        async def zrevrange(self, key, start, stop):
            return [r["id"] for r in items[start:stop + 1]]

        async def mget(self, keys):
            by_id = {r["id"]: r for r in items}
            return [json.dumps(by_id[key.rsplit(":", 1)[-1]]) for key in keys]

        async def aclose(self):
            pass

    monkeypatch.setattr(source_assets.redis, "from_url", lambda *a, **kw: FakeRedis())
    found = await source_assets.list_references(2)
    assert [r["id"] for r in found] == target_ids[:2]
