import pytest

from api.services.media_generation import FalVideoProvider


class FakeResponse:
    is_error = False
    status_code = 200
    text = ""

    def json(self):
        return {
            "request_id": "fal-proof-1",
            "status_url": "https://queue.fal.run/status/1",
            "response_url": "https://queue.fal.run/result/1",
            "cancel_url": "https://queue.fal.run/cancel/1",
        }


class FakeClient:
    def __init__(self, calls, *args, **kwargs):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, headers, json):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse()


def _provider(monkeypatch, calls):
    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setenv("FAL_TEXT_VIDEO_MODEL", "configured/text-model")
    monkeypatch.setenv("FAL_IMAGE_VIDEO_MODEL", "configured/image-model")
    monkeypatch.delenv("FAL_AUDIO_INPUT_FIELD", raising=False)
    monkeypatch.delenv("FAL_IMAGE_INPUT_FIELD", raising=False)
    monkeypatch.delenv("FAL_DURATION_TYPE", raising=False)
    monkeypatch.setattr(
        "api.services.media_generation.httpx.AsyncClient",
        lambda *args, **kwargs: FakeClient(calls, *args, **kwargs),
    )
    return FalVideoProvider()


@pytest.mark.asyncio
async def test_text_video_uses_integer_duration_and_omits_unsupported_audio(monkeypatch):
    calls = []
    provider = _provider(monkeypatch, calls)

    result = await provider.submit_video(
        prompt="test prompt",
        duration="10",
        aspect_ratio="9:16",
        generate_audio=True,
    )

    assert result["ok"] is True
    assert calls[0]["json"] == {
        "prompt": "test prompt",
        "duration": 10,
        "aspect_ratio": "9:16",
    }


@pytest.mark.asyncio
async def test_duration_can_be_sent_as_string_for_models_that_require_it(monkeypatch):
    calls = []
    _provider(monkeypatch, calls)
    monkeypatch.setenv("FAL_DURATION_TYPE", "string")
    provider = FalVideoProvider()

    await provider.submit_video(
        prompt="native audio creator ad",
        duration="10",
        aspect_ratio="9:16",
    )

    assert calls[0]["json"]["duration"] == "10"


@pytest.mark.asyncio
async def test_image_video_uses_configurable_image_field_with_h3_safe_default(monkeypatch):
    calls = []
    provider = _provider(monkeypatch, calls)

    await provider.submit_video(
        prompt="continue the creator shot",
        image_url="https://example.com/frame.jpg",
        duration="10",
    )

    assert calls[0]["json"] == {
        "image_url": "https://example.com/frame.jpg",
        "prompt": "continue the creator shot",
        "duration": 10,
    }


@pytest.mark.asyncio
async def test_audio_capability_is_opt_in_by_environment(monkeypatch):
    calls = []
    _provider(monkeypatch, calls)
    monkeypatch.setenv("FAL_AUDIO_INPUT_FIELD", "generate_audio")
    provider = FalVideoProvider()

    await provider.submit_video(
        prompt="spoken creator ad",
        duration="10",
        generate_audio=True,
    )

    assert calls[0]["json"]["generate_audio"] is True


@pytest.mark.asyncio
async def test_image_field_can_be_overridden_for_another_model(monkeypatch):
    calls = []
    _provider(monkeypatch, calls)
    monkeypatch.setenv("FAL_IMAGE_INPUT_FIELD", "start_image_url")
    provider = FalVideoProvider()

    await provider.submit_video(
        prompt="product shot",
        image_url="https://example.com/product.jpg",
        duration="5",
    )

    assert calls[0]["json"]["start_image_url"] == "https://example.com/product.jpg"
    assert "image_url" not in calls[0]["json"]
