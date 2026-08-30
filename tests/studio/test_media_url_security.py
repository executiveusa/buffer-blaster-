import pytest

from api.services.media_generation import FalVideoProvider


@pytest.mark.asyncio
async def test_fal_fetch_rejects_non_queue_host(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setenv("FAL_QUEUE_URL", "https://queue.fal.run")
    provider = FalVideoProvider()
    result = await provider.fetch_url("https://example.com/steal")
    assert result == {"ok": False, "error": "invalid_fal_url_origin"}


@pytest.mark.asyncio
async def test_fal_fetch_rejects_queue_prefix_spoof(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setenv("FAL_QUEUE_URL", "https://queue.fal.run")
    provider = FalVideoProvider()
    result = await provider.fetch_url("https://queue.fal.run.attacker.example/status")
    assert result == {"ok": False, "error": "invalid_fal_url_origin"}
