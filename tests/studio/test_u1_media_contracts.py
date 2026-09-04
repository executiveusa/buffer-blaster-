from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from api.services.media_contracts import CreativeSource, ProviderCapabilities, UGCPlanDraft
from api.services import media_receipts


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
PRODUCT_ID = "10000000-0000-0000-0000-000000000001"
CREATOR_ID = "20000000-0000-0000-0000-000000000001"


def _draft(**changes):
    payload = {
        "product_source_refs": [PRODUCT_ID],
        "script": "I tried this because the old routine kept wasting time.",
        "shot_plan": [{"shot": 1, "purpose": "hook"}],
        "estimated_cost_ceiling_cents": 0,
        "idempotency_key": "u1-test-plan-001",
    }
    payload.update(changes)
    return UGCPlanDraft(**payload)


def _creator_source(**changes):
    payload = {
        "workspace_id": WORKSPACE_ID,
        "kind": "creator_image",
        "uri": "private://creator/reference.png",
        "sha256": "a" * 64,
        "mime_type": "image/png",
        "owner": "client",
        "rights_state": "owned",
    }
    payload.update(changes)
    return CreativeSource(**payload)


def test_source_contract_requires_explicit_creator_consent():
    with pytest.raises(ValidationError):
        _creator_source()

    source = _creator_source(
        sha256="A" * 64,
        consent_state="granted",
        provider_export_allowed=True,
    )
    assert source.sha256 == "a" * 64
    assert source.provider_export_allowed is True


def test_source_contract_fails_closed_on_provider_export_rights_and_pending_consent():
    with pytest.raises(ValidationError):
        _creator_source(
            rights_state="authorized_analysis",
            consent_state="granted",
            provider_export_allowed=True,
        )
    with pytest.raises(ValidationError):
        _creator_source(
            rights_state="owned",
            consent_state="pending",
            provider_export_allowed=True,
        )


def test_ugc_plan_contract_requires_cost_idempotency_and_creator_rights():
    with pytest.raises(ValidationError):
        _draft(estimated_cost_ceiling_cents=-1)
    with pytest.raises(ValidationError):
        _draft(idempotency_key="short")
    with pytest.raises(ValidationError):
        _draft(creator_source_ref=CREATOR_ID)

    plan = _draft(creator_source_ref=CREATOR_ID, consent_rights_refs=["consent:creator-001"])
    assert plan.estimated_cost_ceiling_cents == 0
    assert plan.finish_mode == "raw_ugc"
    assert plan.provider_preference == "auto"


def test_provider_capabilities_are_provider_neutral():
    capabilities = ProviderCapabilities(
        provider="test-provider",
        image_to_video=True,
        deployment="hosted",
        commercial_use_status="review_required",
    )
    assert capabilities.image_to_video is True
    assert capabilities.health == "unverified"


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


@pytest.mark.asyncio
async def test_redis_fallback_replays_same_idempotent_plan(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_ID)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    async def fake_client():
        return fake

    monkeypatch.setattr(media_receipts, "_redis_client", fake_client)

    first = await media_receipts.create_ugc_plan(_draft())
    second = await media_receipts.create_ugc_plan(_draft())

    assert first["ok"] is True
    assert first["created"] is True
    assert first["paid_generation"] is False
    assert second["ok"] is True
    assert second["created"] is False
    assert second["idempotent_replay"] is True
    assert second["plan"]["plan_id"] == first["plan"]["plan_id"]
    assert UUID(second["plan"]["workspace_id"]) == UUID(WORKSPACE_ID)


@pytest.mark.asyncio
async def test_get_plan_is_scoped_to_configured_workspace(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_ID)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    async def fake_client():
        return fake

    monkeypatch.setattr(media_receipts, "_redis_client", fake_client)
    created = await media_receipts.create_ugc_plan(_draft(idempotency_key="u1-test-plan-read"))
    found = await media_receipts.get_ugc_plan(created["plan"]["plan_id"])
    assert found["ok"] is True
    assert found["plan"]["workspace_id"] == WORKSPACE_ID

    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "00000000-0000-0000-0000-000000000002")
    isolated = await media_receipts.get_ugc_plan(created["plan"]["plan_id"])
    assert isolated["ok"] is False
    assert isolated["error"] == "ugc_plan_not_found"


def test_u1_rest_mcp_cli_use_same_no_spend_contract():
    rest = (ROOT / "api/routers/media_receipts.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    cli = (ROOT / "cli/blaster.py").read_text(encoding="utf-8")
    service = (ROOT / "api/services/media_receipts.py").read_text(encoding="utf-8")

    assert '@router.post("/plans")' in rest
    assert '@router.get("/plans/{plan_id}")' in rest
    assert "create_ugc_plan" in rest and "get_ugc_plan" in rest

    assert '"name": "create_ugc_plan"' in mcp
    assert '"name": "get_ugc_plan"' in mcp
    assert "await create_ugc_plan(UGCPlanDraft(**args))" in mcp
    assert "await get_ugc_plan" in mcp

    assert "ugc-plan-create" in cli
    assert "ugc-plan-get" in cli
    assert '"/api/studio/ugc/plans"' in cli
    assert 'f"/api/studio/ugc/plans/{quote(args[1], safe=\'\')}"' in cli

    assert "media_generation" not in service
    assert "reserve_generation" not in service
    assert '"paid_generation": False' in service


def test_u1_migration_is_additive_rls_and_workspace_scoped():
    sql = (ROOT / "supabase/migrations/013_ugc_canonical_receipts.sql").read_text(encoding="utf-8").lower()
    for table in ["creative_sources", "strategy_receipts", "ugc_plans", "media_takes"]:
        assert f"create table if not exists buffer_blaster.{table}" in sql
        assert f"alter table buffer_blaster.{table} enable row level security" in sql
    assert "unique (workspace_id, idempotency_key)" in sql
    assert "foreign key (workspace_id, creator_source_ref)" in sql
    assert "foreign key (workspace_id, strategy_receipt_ref)" in sql
    assert "foreign key (workspace_id, plan_id)" in sql
    assert "provider_export_allowed or rights_state in ('owned','licensed')" in sql
    assert "estimated_cost_ceiling_cents integer not null" in sql
    assert "drop table" not in sql
    assert "drop schema" not in sql
