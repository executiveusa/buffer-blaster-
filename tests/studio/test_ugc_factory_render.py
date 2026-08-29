import pytest

from api.services.ugc_factory import UGCFactoryBrief
from api.services.ugc_factory_render import render_ugc_factory_clip


class FakeMediaProvider:
    def __init__(self):
        self.calls = []

    async def submit_video(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": True,
            "provider": "fal",
            "model": "env-selected-model",
            "request_id": "render-proof-123",
            "status_url": "https://queue.example/status/123",
            "response_url": "https://queue.example/result/123",
            "cancel_url": "https://queue.example/cancel/123",
        }


def _brief():
    return UGCFactoryBrief(
        product="Cella Coffee",
        audience="home baristas",
        pain="my coffee keeps tasting flat even when the beans are good",
        mechanism="the brew variables stay simple and repeatable",
        offer="POUR15",
        platform="instagram",
    )


@pytest.mark.asyncio
async def test_factory_render_refuses_paid_call_without_approval(monkeypatch):
    provider = FakeMediaProvider()
    monkeypatch.setattr("api.services.ugc_factory_render.get_media_provider", lambda: provider)

    result = await render_ugc_factory_clip(_brief(), clip_number=1, approved=False)

    assert result["ok"] is False
    assert result["error"] == "human_approval_required"
    assert result["approval_required"] is True
    assert provider.calls == []


@pytest.mark.asyncio
async def test_factory_render_submits_approved_compiled_prompt_verbatim(monkeypatch):
    provider = FakeMediaProvider()
    monkeypatch.setattr("api.services.ugc_factory_render.get_media_provider", lambda: provider)

    result = await render_ugc_factory_clip(_brief(), clip_number=1, approved=True)

    assert result["ok"] is True
    assert result["factory_version"] == "ugc-ad-factory-v1"
    assert result["clip"] == 1
    assert result["state"] == "render_queued"
    assert result["request_id"] == "render-proof-123"
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["prompt"] == result["compiled_prompt"]
    assert call["duration"] == "10"
    assert call["aspect_ratio"] == "9:16"


@pytest.mark.asyncio
async def test_factory_render_can_use_reference_image(monkeypatch):
    provider = FakeMediaProvider()
    monkeypatch.setattr("api.services.ugc_factory_render.get_media_provider", lambda: provider)

    await render_ugc_factory_clip(
        _brief(),
        clip_number=1,
        approved=True,
        image_url="https://example.com/product.jpg",
    )

    assert provider.calls[0]["image_url"] == "https://example.com/product.jpg"
