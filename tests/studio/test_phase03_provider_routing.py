from pathlib import Path

import pytest

from api.services.media_contracts import ProviderCapabilities
from api.services.provider_registry import ProviderRegistryEntry, ProviderRouteRequest
from api.services import provider_registry as routing

ROOT = Path(__file__).resolve().parents[2]


def _entry(
    provider: str,
    *,
    cost: int = 25,
    latency: int = 20,
    quality: int = 50,
    deployment: str = "hosted",
    health: str = "ready",
    commercial: str = "approved",
    image_to_video: bool = True,
    text_to_video: bool = True,
    lip_sync: bool = False,
    audio_driven: bool = False,
    body_motion: bool = False,
    max_refs: int = 3,
) -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        capabilities=ProviderCapabilities(
            provider=provider,
            image_to_video=image_to_video,
            text_to_video=text_to_video,
            max_reference_images=max_refs,
            lip_sync=lip_sync,
            audio_driven=audio_driven,
            body_motion=body_motion,
            deployment=deployment,
            supported_ratios=["9:16", "16:9"],
            supported_durations_seconds=[10, 30],
            estimated_cost_cents=cost,
            estimated_latency_seconds=latency,
            commercial_use_status=commercial,
            health=health,
        ),
        quality_rank=quality,
        cost_class="standard",
        provenance="synthetic_test",
    )


def _request(**changes) -> ProviderRouteRequest:
    payload = {
        "capability": "image_to_video",
        "reference_count": 1,
        "aspect_ratio": "9:16",
        "duration_seconds": 10,
        "idempotency_key": "phase03-route-001",
    }
    payload.update(changes)
    return ProviderRouteRequest(**payload)


@pytest.mark.asyncio
async def test_auto_route_prefers_lowest_cost_and_is_idempotent(monkeypatch):
    monkeypatch.setenv("UGC_ROUTE_MAX_COST_CENTS", "200")
    monkeypatch.setattr(routing, "provider_registry", lambda: [
        _entry("premium", cost=90, quality=95),
        _entry("economy", cost=15, quality=45),
    ])

    first = await routing.plan_provider_route(_request())
    second = await routing.plan_provider_route(_request())

    assert first["ok"] is True
    assert first["provider"] == "economy"
    assert first["route_id"] == second["route_id"]
    assert first["request_fingerprint"] == second["request_fingerprint"]
    assert first["paid_generation"] is False
    assert first["spend_reserved"] is False
    assert first["approval_required_before_execution"] is True
    assert first["wallet_authority_unchanged"] is True


@pytest.mark.asyncio
async def test_provider_fallback_skips_unavailable_and_restricted(monkeypatch):
    monkeypatch.setattr(routing, "provider_registry", lambda: [
        _entry("offline", cost=1, health="unavailable"),
        _entry("restricted", cost=2, commercial="restricted"),
        _entry("fallback", cost=30),
    ])

    result = await routing.plan_provider_route(_request(idempotency_key="phase03-fallback-001"))
    assert result["ok"] is True
    assert result["provider"] == "fallback"
    rejected = {item["provider"] for item in result["rejected"]}
    assert {"offline", "restricted"}.issubset(rejected)


@pytest.mark.asyncio
async def test_no_provider_and_insufficient_budget_fail_closed(monkeypatch):
    monkeypatch.setattr(routing, "provider_registry", lambda: [_entry("expensive", cost=80)])
    result = await routing.plan_provider_route(
        _request(idempotency_key="phase03-budget-001", requested_cost_ceiling_cents=20)
    )
    assert result["ok"] is False
    assert result["error"] == "no_eligible_provider"
    assert result["effective_cost_ceiling_cents"] == 20
    assert result["rejected"][0]["reason"] == "insufficient_budget"
    assert result["paid_generation"] is False


@pytest.mark.asyncio
async def test_identity_route_requires_consent(monkeypatch):
    monkeypatch.setattr(routing, "provider_registry", lambda: [
        _entry("avatar", lip_sync=True, audio_driven=True)
    ])
    denied = await routing.plan_provider_route(
        _request(
            capability="talking_creator",
            requires_person_identity=True,
            idempotency_key="phase03-consent-001",
        )
    )
    assert denied == {"ok": False, "error": "identity_consent_required", "paid_generation": False}

    allowed = await routing.plan_provider_route(
        _request(
            capability="talking_creator",
            requires_person_identity=True,
            consent_refs=["consent:creator-001"],
            idempotency_key="phase03-consent-002",
        )
    )
    assert allowed["ok"] is True
    assert allowed["provider"] == "avatar"


@pytest.mark.asyncio
async def test_sovereign_route_rejects_hosted_and_prefers_local(monkeypatch):
    monkeypatch.setattr(routing, "provider_registry", lambda: [
        _entry("hosted-cheap", cost=1, deployment="hosted"),
        _entry("hybrid", cost=20, deployment="hybrid"),
        _entry("local", cost=30, deployment="local"),
    ])
    result = await routing.plan_provider_route(
        _request(preference="sovereign", idempotency_key="phase03-sovereign-001")
    )
    assert result["ok"] is True
    assert result["provider"] == "local"
    assert result["deployment"] == "local"


@pytest.mark.asyncio
async def test_wallet_can_only_lower_server_ceiling(monkeypatch):
    monkeypatch.setenv("UGC_ROUTE_MAX_COST_CENTS", "200")
    monkeypatch.setattr(routing, "provider_registry", lambda: [_entry("provider", cost=60)])

    async def fake_wallet(_wallet_id):
        return {"state": "active", "remaining_provider_budget_cents": 40}

    monkeypatch.setattr(routing, "get_wallet", fake_wallet)
    result = await routing.plan_provider_route(
        _request(wallet_id="wallet-1", requested_cost_ceiling_cents=500, idempotency_key="phase03-wallet-001")
    )
    assert result["ok"] is False
    assert result["effective_cost_ceiling_cents"] == 40
    assert result["rejected"][0]["reason"] == "insufficient_budget"


def test_rest_mcp_cli_share_no_spend_provider_route_contract():
    rest = (ROOT / "api/routers/provider_routes.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    cli = (ROOT / "cli/blaster.py").read_text(encoding="utf-8")
    service = (ROOT / "api/services/provider_registry.py").read_text(encoding="utf-8")

    assert '@router.get("/capabilities")' in rest
    assert '@router.post("/route")' in rest
    assert "plan_provider_route(request)" in rest

    assert '"name": "list_provider_capabilities"' in mcp
    assert '"name": "plan_provider_route"' in mcp
    assert "ProviderRouteRequest(**args)" in mcp

    assert "provider-capabilities" in cli
    assert "provider-route" in cli
    assert '"/api/studio/providers/capabilities"' in cli
    assert '"/api/studio/providers/route"' in cli

    assert "reserve_generation" not in service
    assert "execute_ugc_factory_ad" not in service
    assert '"paid_generation": False' in service
    assert '"spend_reserved": False' in service
