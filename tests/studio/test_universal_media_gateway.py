from pathlib import Path

import pytest

from api.services.media_generation import FalVideoProvider, get_media_provider
from api.services.provider_contracts import UGCProviderJob
from api.services.universal_media_gateway import UniversalVideoGatewayProvider


ROOT = Path(__file__).resolve().parents[2]


def _configure_gateway(monkeypatch):
    monkeypatch.setenv("ACTIVE_MEDIA_PROVIDER", "gateway")
    monkeypatch.setenv("GENERATION_GATEWAY_NAME", "muapi")
    monkeypatch.setenv("GENERATION_GATEWAY_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("GENERATION_GATEWAY_API_KEY", "synthetic")
    monkeypatch.setenv("GENERATION_GATEWAY_TEXT_VIDEO_MODEL", "seedance-2.5")
    monkeypatch.setenv("GENERATION_GATEWAY_IMAGE_VIDEO_MODEL", "seedance-2.5")
    monkeypatch.setenv("GENERATION_GATEWAY_ALLOWED_MODELS", "seedance-2.5,kling-3.0,veo-3.1")
    monkeypatch.setenv("GENERATION_GATEWAY_SUBMIT_PATH", "/api/v1/{model}")
    monkeypatch.setenv("GENERATION_GATEWAY_STATUS_PATH", "/api/v1/predictions/{id}/result")
    monkeypatch.setenv("GENERATION_GATEWAY_AUTH_HEADER", "x-api-key")
    monkeypatch.setenv("GENERATION_GATEWAY_AUTH_PREFIX", "")
    monkeypatch.setenv("GENERATION_GATEWAY_MODEL_IN_BODY", "false")
    monkeypatch.setenv("GENERATION_GATEWAY_ESTIMATED_CLIP_COST_CENTS", "42")
    monkeypatch.setenv("GENERATION_GATEWAY_MODEL_COSTS_JSON", '{"seedance-2.5":42,"kling-3.0":55,"veo-3.1":120}')
    monkeypatch.setenv("GENERATION_GATEWAY_COMMERCIAL_USE_STATUS", "approved")


def _job(**changes):
    payload = {
        "script": "A concise product demo.",
        "prompt": "Natural vertical creator video.",
        "estimated_cost_ceiling_cents": 100,
        "idempotency_key": "gateway-job-001",
    }
    payload.update(changes)
    return UGCProviderJob(**payload)


def test_runtime_provider_switch_is_configuration_owned(monkeypatch):
    _configure_gateway(monkeypatch)
    provider = get_media_provider()
    assert isinstance(provider, UniversalVideoGatewayProvider)
    assert provider.status()["provider"] == "muapi"
    assert provider.models() == ["kling-3.0", "seedance-2.5", "veo-3.1"]

    monkeypatch.setenv("ACTIVE_MEDIA_PROVIDER", "fal")
    assert isinstance(get_media_provider(), FalVideoProvider)


def test_gateway_plan_accepts_allowlisted_model_and_rejects_unknown(monkeypatch):
    _configure_gateway(monkeypatch)
    provider = UniversalVideoGatewayProvider()

    planned = provider.plan_job(_job(model_name="seedance-2.5"))
    assert planned.provider == "muapi"
    assert planned.model_name == "seedance-2.5"
    assert planned.estimated_cost_cents == 42

    rejected = provider.plan_job(_job(model_name="not-allowed"))
    assert rejected.model_name is None


@pytest.mark.asyncio
async def test_gateway_blocks_unapproved_job_before_network(monkeypatch):
    _configure_gateway(monkeypatch)
    provider = UniversalVideoGatewayProvider()
    result = await provider.submit_job(_job(model_name="seedance-2.5", approval_state="draft"))
    assert result.state == "spend_blocked"
    assert result.failure["error"] == "approval_required"


def test_factory_and_rest_surface_carry_model_without_hardcoding_vendor_ids():
    factory = (ROOT / "api/services/ugc_factory.py").read_text(encoding="utf-8")
    executor = (ROOT / "api/services/ugc_executor.py").read_text(encoding="utf-8")
    router = (ROOT / "api/routers/studio.py").read_text(encoding="utf-8")
    provider_routes = (ROOT / "api/routers/provider_routes.py").read_text(encoding="utf-8")

    assert "provider_model" in factory
    assert "provider_model" in executor
    assert "provider_model" in router
    assert '@router.get("/models")' in provider_routes

    # Business logic carries a selected model string but does not bake in a model family.
    assert "seedance-2.5" not in factory.lower()
    assert "kling-3.0" not in factory.lower()
    assert "veo-3.1" not in factory.lower()


def test_gateway_model_override_fails_closed_without_allowlist(monkeypatch):
    _configure_gateway(monkeypatch)
    monkeypatch.setenv("GENERATION_GATEWAY_ALLOWED_MODELS", "")
    provider = UniversalVideoGatewayProvider()

    assert provider.plan_job(_job(model_name="seedance-2.5")).model_name == "seedance-2.5"
    assert provider.plan_job(_job(model_name="kling-3.0")).model_name is None


def test_gateway_override_requires_verified_cost(monkeypatch):
    _configure_gateway(monkeypatch)
    monkeypatch.setenv("GENERATION_GATEWAY_MODEL_COSTS_JSON", '{"seedance-2.5":42}')
    provider = UniversalVideoGatewayProvider()

    assert provider.estimate_clip_cost_cents("seedance-2.5") == 42
    assert provider.estimate_clip_cost_cents("kling-3.0") is None


def test_self_hosted_http_origin_is_allowed_only_when_exact(monkeypatch):
    _configure_gateway(monkeypatch)
    monkeypatch.setenv("GENERATION_GATEWAY_BASE_URL", "http://gateway:8000")
    provider = UniversalVideoGatewayProvider()

    assert provider._same_origin("http://gateway:8000/v1/videos/task-1") is True
    assert provider._same_origin("https://gateway:8000/v1/videos/task-1") is False
    assert provider._same_origin("http://other:8000/v1/videos/task-1") is False


def test_studio_prices_selected_model_before_wallet_reservation():
    router = (ROOT / "api/routers/studio.py").read_text(encoding="utf-8")
    pricing_index = router.index("estimate_factory_generation_cost(provider, plan, provider_model)")
    reserve_index = router.index("reservation = await reserve_generation(")
    assert pricing_index < reserve_index
    assert 'estimated_provider_cost_cents=estimated_cost' in router
