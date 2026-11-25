from pathlib import Path

import pytest

from api.services.media_generation import get_media_provider
from api.services.provider_contracts import UGCProviderJob
from api.services.sand_video import SandVideoProvider


ROOT = Path(__file__).resolve().parents[2]


def _job(**changes) -> UGCProviderJob:
    payload = {
        "script": "I kept running into the same problem, so I tried a simpler routine.",
        "prompt": "Natural creator-style vertical video with restrained camera movement.",
        "estimated_cost_ceiling_cents": 200,
        "idempotency_key": "sand-provider-job-001",
    }
    payload.update(changes)
    return UGCProviderJob(**payload)


def _configure(monkeypatch):
    monkeypatch.setenv("SAND_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("SAND_MODEL", "magi-2")
    monkeypatch.setenv("SAND_ALLOWED_MODELS", "magi-2")
    monkeypatch.setenv("SAND_COST_PER_SECOND_CENTS", "8")
    monkeypatch.setenv("SAND_SUPPORTED_RATIOS", "9:16,16:9")
    monkeypatch.setenv("SAND_SUPPORTED_DURATIONS_SECONDS", "5,10")


def test_sand_capabilities_and_plan_are_configuration_owned(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    capabilities = provider.capabilities()
    assert capabilities.provider == "sand"
    assert capabilities.text_to_video is True
    assert capabilities.image_to_video is True
    assert capabilities.health == "ready"
    assert capabilities.commercial_use_status == "review_required"

    planned = provider.plan_job(_job(duration_seconds=10))
    assert planned.provider == "sand"
    assert planned.model_name == "magi-2"
    assert planned.estimated_cost_cents == 80  # 8 cents/s * 10 s
    assert planned.state == "planned"


def test_sand_cost_scales_with_duration(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    assert provider.estimate_clip_cost_cents(duration_seconds=20) == 160
    assert provider.estimate_clip_cost_cents(model_name="other-model") is None


def test_sand_selected_via_active_media_provider(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setenv("ACTIVE_MEDIA_PROVIDER", "sand")
    assert isinstance(get_media_provider(), SandVideoProvider)
    monkeypatch.setenv("ACTIVE_MEDIA_PROVIDER", "fal")
    from api.services.media_generation import FalVideoProvider

    assert isinstance(get_media_provider(), FalVideoProvider)


@pytest.mark.asyncio
async def test_sand_blocks_unapproved_spend_before_network(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    called = False

    async def should_not_submit(**_kwargs):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr(provider, "submit_video", should_not_submit)
    job = _job(approval_state="draft")
    planned = await provider.submit_job(job)
    assert planned.state == "spend_blocked"
    assert planned.failure["error"] == "approval_required"
    assert called is False


@pytest.mark.asyncio
async def test_sand_blocks_cost_over_ceiling_before_network(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    called = False

    async def should_not_submit(**_kwargs):
        nonlocal called
        called = True
        return {"ok": True}

    monkeypatch.setattr(provider, "submit_video", should_not_submit)
    # 8 cents/s * 300 s = 2400 cents, above the 200-cent ceiling
    job = _job(approval_state="approved", duration_seconds=300)
    planned = await provider.submit_job(job)
    assert planned.state == "spend_blocked"
    assert planned.failure["error"] == "estimated_cost_exceeds_ceiling"
    assert called is False


@pytest.mark.asyncio
async def test_sand_submit_builds_native_parts_payload(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    captured = {}

    class FakeResponse:
        is_error = False

        def json(self):
            return {"id": "123456789", "status": "queued"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("api.services.sand_video.httpx.AsyncClient", FakeClient)
    receipt = await provider.submit_video(
        prompt="Creator talks to camera about the routine.",
        image_url="https://assets.example/creator.png",
        duration="10",
        aspect_ratio="9:16",
    )
    assert receipt["ok"] is True
    assert receipt["provider"] == "sand"
    assert receipt["request_id"] == "123456789"
    assert receipt["status_url"] == "https://api.sand.ai/v2/generations/123456789"
    assert captured["url"] == "https://api.sand.ai/v2/generations"
    assert captured["headers"]["Authorization"] == "Bearer synthetic-test-key"
    assert captured["json"]["model"] == "magi-2"
    assert captured["json"]["duration"] == 10
    assert captured["json"]["aspectRatio"] == "9:16"
    assert captured["json"]["parts"] == [
        {"type": "text", "text": "Creator talks to camera about the routine."},
        {"type": "reference_image", "image": {"url": "https://assets.example/creator.png"}},
    ]


@pytest.mark.asyncio
async def test_sand_fetch_url_rejects_foreign_origin(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    result = await provider.fetch_url("https://evil.example/v2/generations/1")
    assert result["ok"] is False
    assert result["error"] == "invalid_sand_url_origin"


@pytest.mark.asyncio
async def test_sand_submit_rejects_non_https_reference(monkeypatch):
    _configure(monkeypatch)
    provider = SandVideoProvider()
    result = await provider.submit_video(
        prompt="test",
        image_url="http://assets.example/creator.png",
        duration="5",
    )
    assert result["ok"] is False
    assert result["error"] == "sand_reference_requires_https"


def test_sand_unconfigured_without_key(monkeypatch):
    monkeypatch.delenv("SAND_API_KEY", raising=False)
    provider = SandVideoProvider()
    assert provider.configured is False
    assert provider.capabilities().health == "unavailable"
