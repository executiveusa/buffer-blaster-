import pytest

from api.services.publishing import (
    BufferPublishingProvider,
    DisabledPublishingProvider,
    PublishRequest,
    get_publisher,
)


@pytest.mark.asyncio
async def test_disabled_publishing_refuses_unapproved_publish():
    publisher = DisabledPublishingProvider()
    result = await publisher.schedule(PublishRequest(
        content="Test content",
        platforms=[{"platform": "instagram"}],
        scheduled_at="2026-09-01T12:00:00Z",
        approved=False,
    ))
    assert result["ok"] is False
    assert result["error"] == "human_approval_required"


@pytest.mark.asyncio
async def test_disabled_publishing_status_reports_not_required_for_core(monkeypatch):
    monkeypatch.delenv("PUBLISHING_PROVIDER", raising=False)
    publisher = get_publisher()
    status = publisher.status()
    assert status["enabled"] is False
    assert status["provider"] is None
    assert status["required_for_core"] is False


@pytest.mark.asyncio
async def test_disabled_publishing_list_accounts_returns_empty(monkeypatch):
    monkeypatch.delenv("PUBLISHING_PROVIDER", raising=False)
    publisher = get_publisher()
    accounts = await publisher.list_accounts()
    assert accounts["ok"] is False
    assert accounts["error"] == "publishing_integration_disabled"
    assert accounts["accounts"] == []


@pytest.mark.asyncio
async def test_disabled_publishing_schedule_returns_disabled(monkeypatch):
    monkeypatch.delenv("PUBLISHING_PROVIDER", raising=False)
    publisher = get_publisher()
    result = await publisher.schedule(PublishRequest(
        content="Test content",
        platforms=[{"platform": "instagram"}],
        scheduled_at="2026-09-01T12:00:00Z",
        approved=True,
    ))
    assert result["ok"] is False
    assert result["error"] == "publishing_integration_disabled"


def test_buffer_provider_selected_only_explicitly(monkeypatch):
    monkeypatch.setenv("PUBLISHING_PROVIDER", "buffer")
    monkeypatch.setenv("BUFFER_API_KEY", "test-only-token")
    publisher = get_publisher()
    assert isinstance(publisher, BufferPublishingProvider)
    assert publisher.status() == {
        "enabled": True,
        "provider": "buffer",
        "configured": True,
        "required_for_core": False,
    }


@pytest.mark.asyncio
async def test_buffer_refuses_unapproved_publish(monkeypatch):
    monkeypatch.setenv("BUFFER_API_KEY", "test-only-token")
    publisher = BufferPublishingProvider()
    result = await publisher.schedule(PublishRequest(
        content="Test content",
        platforms=[{"social_account_id": "channel-1"}],
        scheduled_at="2026-09-01T12:00:00Z",
        approved=False,
    ))
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_buffer_requires_server_token(monkeypatch):
    monkeypatch.delenv("BUFFER_API_KEY", raising=False)
    publisher = BufferPublishingProvider()
    result = await publisher.schedule(PublishRequest(
        content="Test content",
        platforms=[{"social_account_id": "channel-1"}],
        scheduled_at="2026-09-01T12:00:00Z",
        approved=True,
    ))
    assert result == {"ok": False, "error": "buffer_not_configured"}


@pytest.mark.asyncio
async def test_buffer_list_accounts_normalizes_channels(monkeypatch):
    monkeypatch.setenv("BUFFER_API_KEY", "test-only-token")
    publisher = BufferPublishingProvider()

    async def fake_org():
        return "org-1"

    async def fake_graphql(query, variables=None):
        assert variables == {"organizationId": "org-1"}
        return {
            "ok": True,
            "data": {
                "channels": [
                    {
                        "id": "channel-1",
                        "name": "fallback",
                        "displayName": "Brand IG",
                        "service": "instagram",
                        "isQueuePaused": False,
                    }
                ]
            },
        }

    monkeypatch.setattr(publisher, "_organization_id", fake_org)
    monkeypatch.setattr(publisher, "_graphql", fake_graphql)
    result = await publisher.list_accounts()
    assert result["ok"] is True
    assert result["provider"] == "buffer"
    assert result["accounts"] == [
        {
            "social_account_id": "channel-1",
            "name": "Brand IG",
            "platform": "instagram",
            "queue_paused": False,
        }
    ]


@pytest.mark.asyncio
async def test_buffer_schedule_uses_channel_and_returns_receipt(monkeypatch):
    monkeypatch.setenv("BUFFER_API_KEY", "test-only-token")
    publisher = BufferPublishingProvider()
    calls = []

    async def fake_graphql(query, variables=None):
        calls.append((query, variables))
        return {
            "ok": True,
            "data": {
                "createPost": {
                    "post": {
                        "id": "post-1",
                        "text": "Launch",
                        "status": "scheduled",
                        "dueAt": "2026-09-03T12:00:00Z",
                    }
                }
            },
        }

    monkeypatch.setattr(publisher, "_graphql", fake_graphql)
    result = await publisher.schedule(PublishRequest(
        content="Launch",
        platforms=[{"social_account_id": "channel-1", "platform": "instagram"}],
        scheduled_at="2026-09-03T12:00:00Z",
        approved=True,
        media_urls=["https://cdn.example.com/ad.mp4"],
    ))
    assert result["ok"] is True
    assert result["provider"] == "buffer"
    assert result["receipts"][0]["external_post_id"] == "post-1"
    post_input = calls[0][1]["input"]
    assert post_input["channelId"] == "channel-1"
    assert post_input["mode"] == "customScheduled"
    assert post_input["dueAt"] == "2026-09-03T12:00:00Z"
    assert post_input["assets"] == [{"video": {"url": "https://cdn.example.com/ad.mp4"}}]
