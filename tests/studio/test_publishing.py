import pytest
from api.services.publishing import PublishRequest, DisabledPublishingProvider, get_publisher


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
async def test_disabled_publishing_status_reports_not_required_for_core():
    publisher = get_publisher()
    status = publisher.status()
    assert status["enabled"] is False
    assert status["provider"] is None
    assert status["required_for_core"] is False


@pytest.mark.asyncio
async def test_disabled_publishing_list_accounts_returns_empty():
    publisher = get_publisher()
    accounts = await publisher.list_accounts()
    assert accounts["ok"] is False
    assert accounts["error"] == "publishing_integration_disabled"
    assert accounts["accounts"] == []


@pytest.mark.asyncio
async def test_disabled_publishing_schedule_returns_disabled():
    publisher = get_publisher()
    result = await publisher.schedule(PublishRequest(
        content="Test content",
        platforms=[{"platform": "instagram"}],
        scheduled_at="2026-09-01T12:00:00Z",
        approved=True,
    ))
    assert result["ok"] is False
    assert result["error"] == "publishing_integration_disabled"
