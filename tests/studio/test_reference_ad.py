import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services import media_receipts, reference_ad
from api.services.reference_ad import ReferenceAdIntake, analyze_reference_ad, analyze_reference_mechanics


ROOT = Path(__file__).resolve().parents[2]
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


def _intake(**changes):
    payload = {
        "source_uri": "https://reference.example/ad.mp4",
        "source_sha256": "A" * 64,
        "source_owner": "client",
        "rights_state": "authorized_analysis",
        "transcript": (
            "BrandOmega opens with a frustrating problem that kept wasting time. "
            "Then the product is shown in use before an after result. "
            "Try BrandOmega today."
        ),
        "duration_seconds": 24,
        "shot_notes": [
            {"purpose": "hook", "raw": "BrandOmega logo close-up"},
            {"purpose": "demo", "raw": "source packaging"},
            {"purpose": "cta", "raw": "source end card"},
        ],
        "product_source_refs": [PRODUCT_ID],
        "client_product": "Cella Coffee",
        "target_audience": "home baristas",
        "approved_claims": ["The workflow keeps the brew variables visible"],
        "protected_brand_terms": ["BrandOmega"],
        "idempotency_key": "reference-test-001",
    }
    payload.update(changes)
    return ReferenceAdIntake(**payload)


def _wire_fake_store(monkeypatch, fake):
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_ID)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    async def fake_client():
        return fake

    monkeypatch.setattr(reference_ad, "_redis_client", fake_client)
    monkeypatch.setattr(media_receipts, "_redis_client", fake_client)


def test_reference_mechanics_store_labels_not_reference_copy():
    intake = _intake()
    analysis = analyze_reference_mechanics(intake)
    rendered = json.dumps(analysis.model_dump()).lower()
    assert analysis.hook == "problem_first"
    assert analysis.problem == "explicit_friction"
    assert analysis.proof in {"numeric_before_after_or_social_proof", "visual_demonstration"}
    assert analysis.cta == "direct_action"
    assert "brandomega" not in rendered
    assert "source packaging" not in rendered
    assert analysis.shot_structure == [
        {"position": 1, "purpose": "hook"},
        {"position": 2, "purpose": "demo"},
        {"position": 3, "purpose": "cta"},
    ]


@pytest.mark.asyncio
async def test_reference_ad_creates_control_two_challengers_and_replays(monkeypatch):
    fake = _FakeRedis()
    _wire_fake_store(monkeypatch, fake)

    first = await analyze_reference_ad(_intake())
    assert first["ok"] is True
    assert first["paid_generation"] is False
    assert first["created"] is True
    assert len(first["variants"]) == 3
    roles = [plan["metadata"]["variant_role"] for plan in first["variants"]]
    assert roles == ["control", "challenger_hook", "challenger_proof"]
    assert all(plan["estimated_cost_ceiling_cents"] == 0 for plan in first["variants"])
    assert all(plan["approval_state"] == "draft" for plan in first["variants"])
    assert all("brandomega" not in plan["script"].lower() for plan in first["variants"])
    assert first["strategy"]["metadata"]["reference_copy_stored"] is False
    assert len(first["strategy"]["metadata"]["variant_plan_ids"]) == 3

    second = await analyze_reference_ad(_intake())
    assert second["ok"] is True
    assert second["created"] is False
    assert second["idempotent_replay"] is True
    assert second["strategy"]["receipt_id"] == first["strategy"]["receipt_id"]
    assert [p["plan_id"] for p in second["variants"]] == [p["plan_id"] for p in first["variants"]]


@pytest.mark.asyncio
async def test_reference_idempotency_key_rejects_different_remix(monkeypatch):
    fake = _FakeRedis()
    _wire_fake_store(monkeypatch, fake)
    first = await analyze_reference_ad(_intake())
    assert first["ok"] is True

    conflict = await analyze_reference_ad(_intake(client_product="Different Product"))
    assert conflict["ok"] is False
    assert conflict["error"] == "idempotency_conflict"


def test_reference_rest_to_mcp_roundtrip_uses_same_receipt(monkeypatch):
    fake = _FakeRedis()
    _wire_fake_store(monkeypatch, fake)
    monkeypatch.setenv("BLASTER_API_KEY", "synthetic-agent-key")
    client = TestClient(app)

    created = client.post(
        "/api/studio/reference-ads/analyze",
        headers={"x-api-key": "synthetic-agent-key"},
        json=_intake().model_dump(mode="json"),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["ok"] is True
    receipt_id = body["strategy"]["receipt_id"]

    read = client.post(
        "/api/mcp",
        headers={"x-api-key": "synthetic-agent-key"},
        json={
            "jsonrpc": "2.0",
            "id": "reference-roundtrip",
            "method": "tools/call",
            "params": {"name": "get_reference_strategy", "arguments": {"receipt_id": receipt_id}},
        },
    )
    assert read.status_code == 200
    result = read.json()["result"]["structuredContent"]
    assert result["ok"] is True
    assert result["strategy"]["receipt_id"] == receipt_id
    assert len(result["variants"]) == 3


def test_reference_interfaces_and_migration_are_governed_and_additive():
    rest = (ROOT / "api/routers/reference_ads.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    cli = (ROOT / "cli/blaster.py").read_text(encoding="utf-8")
    service = (ROOT / "api/services/reference_ad.py").read_text(encoding="utf-8")
    migration = (ROOT / "supabase/migrations/014_reference_strategy_receipts.sql").read_text(encoding="utf-8").lower()

    assert '@router.post("/analyze")' in rest
    assert '@router.get("/strategy/{receipt_id}")' in rest
    assert '"name": "analyze_reference_ad"' in mcp
    assert '"name": "get_reference_strategy"' in mcp
    assert "reference-analyze" in cli and "reference-strategy" in cli
    assert "media_generation" not in service
    assert "reserve_generation" not in service
    assert "get_media_provider" not in service
    assert "add column if not exists idempotency_key" in migration
    assert "add column if not exists metadata" in migration
    assert "strategy_receipts_workspace_idempotency_uq" in migration
    assert "drop table" not in migration
    assert "drop column" not in migration
