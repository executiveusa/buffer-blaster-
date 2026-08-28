import pytest

from api.services.publishing import PublishRequest, TryPostPublisher


@pytest.mark.asyncio
async def test_trypost_refuses_unapproved_publish():
    publisher = TryPostPublisher(base_url="https://example.test", token="test")
    result = await publisher.schedule(PublishRequest(
        content="hello",
        platforms=[{"social_account_id": "acct_1", "content_type": "post"}],
        scheduled_at="2026-08-29T18:00:00Z",
        approved=False,
    ))
    assert result["ok"] is False
    assert result["error"] == "human_approval_required"


@pytest.mark.asyncio
async def test_trypost_builds_documented_post_payload(monkeypatch):
    seen = {}

    class Response:
        status_code = 201
        def raise_for_status(self):
            return None
        def json(self):
            return {"id": "post_1", "status": "scheduled"}

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def post(self, url, headers=None, json=None):
            seen.update({"url": url, "headers": headers, "json": json})
            return Response()

    monkeypatch.setattr("api.services.publishing.httpx.AsyncClient", lambda **_: Client())
    publisher = TryPostPublisher(base_url="https://trypost.example", token="secret")
    result = await publisher.schedule(PublishRequest(
        content="launch day",
        platforms=[{"social_account_id": "acct_1", "content_type": "reel"}],
        scheduled_at="2026-08-29T18:00:00Z",
        approved=True,
    ))
    assert result["ok"] is True
    assert seen["url"] == "https://trypost.example/api/posts"
    assert seen["json"]["content"] == "launch day"
    assert seen["json"]["scheduled_at"].endswith("Z")
    assert seen["json"]["platforms"][0]["social_account_id"] == "acct_1"
