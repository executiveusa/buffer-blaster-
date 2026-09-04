from pathlib import Path

import pytest

from api.services.media_generation import FalVideoProvider
from api.services.provider_contracts import UGCProviderJob


ROOT = Path(__file__).resolve().parents[2]


def _job(**changes) -> UGCProviderJob:
    payload = {
        "script": "I kept running into the same problem, so I tried a simpler routine.",
        "prompt": "Natural creator-style vertical video with restrained camera movement.",
        "estimated_cost_ceiling_cents": 100,
        "idempotency_key": "provider-job-001",
    }
    payload.update(changes)
    return UGCProviderJob(**payload)


def _configure(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "synthetic-test-key")
    monkeypatch.setenv("FAL_TEXT_VIDEO_MODEL", "configured/text-model")
    monkeypatch.setenv("FAL_IMAGE_VIDEO_MODEL", "configured/image-model")
    monkeypatch.setenv("FAL_ESTIMATED_CLIP_COST_CENTS", "80")
    monkeypatch.setenv("FAL_SUPPORTED_RATIOS", "9:16,16:9")
    monkeypatch.setenv("FAL_SUPPORTED_DURATIONS_SECONDS", "5,10")


def test_provider_capabilities_and_plan_are_configuration_owned(monkeypatch):
    _configure(monkeypatch)
    provider = FalVideoProvider()
    capabilities = provider.capabilities()
    assert capabilities.provider == "fal"
    assert capabilities.text_to_video is True
    assert capabilities.image_to_video is True
    assert capabilities.estimated_cost_cents == 80
    assert capabilities.health == "ready"

    planned = provider.plan_job(_job())
    assert planned.provider == "fal"
    assert planned.model_name == "configured/text-model"
    assert planned.estimated_cost_cents == 80
    assert planned.state == "planned"

    image_plan = provider.plan_job(_job(actor_reference_url="https://assets.example/creator.png"))
    assert image_plan.model_name == "configured/image-model"


@pytest.mark.asyncio
async def test_provider_job_blocks_unapproved_spend_before_network(monkeypatch):
    _configure(monkeypatch)
    provider = FalVideoProvider()
    called = False

    async def should_not_submit(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider network call must not run")

    monkeypatch.setattr(provider, "submit_video", should_not_submit)
    result = await provider.submit_job(_job(approval_state="draft"))
    assert result.state == "spend_blocked"
    assert result.failure["error"] == "approval_required"
    assert called is False


@pytest.mark.asyncio
async def test_provider_job_blocks_estimate_above_server_ceiling(monkeypatch):
    _configure(monkeypatch)
    provider = FalVideoProvider()

    async def should_not_submit(**_kwargs):
        raise AssertionError("provider network call must not run")

    monkeypatch.setattr(provider, "submit_video", should_not_submit)
    result = await provider.submit_job(
        _job(approval_state="approved", estimated_cost_ceiling_cents=50)
    )
    assert result.state == "spend_blocked"
    assert result.failure["error"] == "estimated_cost_exceeds_ceiling"


@pytest.mark.asyncio
async def test_provider_job_normalizes_success_and_failure_receipts(monkeypatch):
    _configure(monkeypatch)
    provider = FalVideoProvider()

    async def success(**_kwargs):
        return {
            "ok": True,
            "provider": "fal",
            "model": "configured/text-model",
            "request_id": "synthetic-request",
            "status_url": "https://queue.fal.run/status/synthetic-request",
            "response_url": "https://queue.fal.run/response/synthetic-request",
            "cancel_url": None,
        }

    monkeypatch.setattr(provider, "submit_video", success)
    submitted = await provider.submit_job(_job(approval_state="approved"))
    assert submitted.state == "submitted"
    assert submitted.output_receipt["request_id"] == "synthetic-request"
    assert submitted.failure == {}

    async def failure(**_kwargs):
        return {"ok": False, "error": "synthetic_provider_failure", "status": 503}

    monkeypatch.setattr(provider, "submit_video", failure)
    failed = await provider.submit_job(_job(approval_state="approved"))
    assert failed.state == "failed"
    assert failed.failure["error"] == "synthetic_provider_failure"


def test_provider_contract_is_additive_and_business_logic_has_no_model_ids():
    provider_source = (ROOT / "api/services/media_generation.py").read_text(encoding="utf-8")
    factory_source = (ROOT / "api/services/ugc_factory.py").read_text(encoding="utf-8")
    assert "def submit_video(" in provider_source
    assert "def fetch_url(" in provider_source
    assert "def plan_job(" in provider_source
    assert "def submit_job(" in provider_source
    assert "FAL_TEXT_VIDEO_MODEL" in provider_source
    assert "FAL_IMAGE_VIDEO_MODEL" in provider_source
    assert "seedance" not in factory_source.lower()
    assert "veo" not in factory_source.lower()
    assert "kling" not in factory_source.lower()
