import pytest

from api.services import media_receipts
from api.services.media_contracts import UGCPlanDraft


WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
PRODUCT_ID = "10000000-0000-0000-0000-000000000001"


class _FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, nx=False):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def aclose(self):
        return None


def _draft(key: str) -> UGCPlanDraft:
    return UGCPlanDraft(
        product_source_refs=[PRODUCT_ID],
        script="One variable at a time makes the result explainable.",
        shot_plan=[{"shot": 1, "purpose": "hook"}],
        estimated_cost_ceiling_cents=0,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_missing_workspace_fails_closed_without_provider_or_store_access(monkeypatch):
    monkeypatch.delenv("BUFFER_BLASTER_WORKSPACE_ID", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    result = await media_receipts.create_ugc_plan(_draft("missing-workspace-001"))
    assert result == {
        "ok": False,
        "error": "canonical_workspace_not_configured",
        "paid_generation": False,
        "backend": "unavailable",
    }


@pytest.mark.asyncio
async def test_redis_idempotent_replay_repairs_plan_lookup(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_ID)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    async def fake_client():
        return fake

    monkeypatch.setattr(media_receipts, "_redis_client", fake_client)
    draft = _draft("repair-secondary-001")
    first = await media_receipts.create_ugc_plan(draft)
    plan_id = first["plan"]["plan_id"]
    plan_key = f"buffer_blaster:ugc:plan:v1:{WORKSPACE_ID}:{plan_id}"
    fake.values.pop(plan_key)

    missing = await media_receipts.get_ugc_plan(plan_id)
    assert missing["ok"] is False
    assert missing["error"] == "ugc_plan_not_found"

    replay = await media_receipts.create_ugc_plan(draft)
    assert replay["ok"] is True
    assert replay["created"] is False
    assert replay["idempotent_replay"] is True
    assert replay["plan"]["plan_id"] == plan_id

    repaired = await media_receipts.get_ugc_plan(plan_id)
    assert repaired["ok"] is True
    assert repaired["plan"]["plan_id"] == plan_id
