import json

from fastapi.testclient import TestClient

from api.app import app
from api.services import media_receipts


WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
PRODUCT_ID = "10000000-0000-0000-0000-000000000001"


class _FakeRedis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, nx=False):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)

    async def aclose(self):
        return None


def _payload(idempotency_key: str) -> dict:
    return {
        "product_source_refs": [PRODUCT_ID],
        "script": "I kept changing everything at once, so I could never tell what actually worked.",
        "shot_plan": [{"shot": 1, "purpose": "problem"}, {"shot": 2, "purpose": "proof"}],
        "finish_mode": "raw_ugc",
        "provider_preference": "auto",
        "estimated_cost_ceiling_cents": 0,
        "approval_state": "draft",
        "idempotency_key": idempotency_key,
    }


def _configure(monkeypatch, fake: _FakeRedis) -> None:
    monkeypatch.setenv("BLASTER_API_KEY", "u1-interface-test-key")
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_ID)
    monkeypatch.setenv("REDIS_URL", "redis://synthetic-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    async def fake_client():
        return fake

    monkeypatch.setattr(media_receipts, "_redis_client", fake_client)


def test_rest_create_can_be_read_through_mcp_same_receipt(monkeypatch):
    fake = _FakeRedis()
    _configure(monkeypatch, fake)
    client = TestClient(app)

    created = client.post(
        "/api/studio/ugc/plans",
        headers={"x-api-key": "u1-interface-test-key"},
        json=_payload("rest-to-mcp-u1-001"),
    )
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["ok"] is True
    assert created_body["paid_generation"] is False
    plan_id = created_body["plan"]["plan_id"]

    mcp = client.post(
        "/api/mcp",
        headers={"x-api-key": "u1-interface-test-key"},
        json={
            "jsonrpc": "2.0",
            "id": "u1-read-proof",
            "method": "tools/call",
            "params": {"name": "get_ugc_plan", "arguments": {"plan_id": plan_id}},
        },
    )
    assert mcp.status_code == 200
    result = mcp.json()["result"]["structuredContent"]
    assert result["ok"] is True
    assert result["paid_generation"] is False
    assert result["plan"] == created_body["plan"]


def test_mcp_create_can_be_read_through_rest_and_replays_idempotently(monkeypatch):
    fake = _FakeRedis()
    _configure(monkeypatch, fake)
    client = TestClient(app)
    payload = _payload("mcp-to-rest-u1-001")

    def call_create():
        response = client.post(
            "/api/mcp",
            headers={"x-api-key": "u1-interface-test-key"},
            json={
                "jsonrpc": "2.0",
                "id": "u1-create-proof",
                "method": "tools/call",
                "params": {"name": "create_ugc_plan", "arguments": payload},
            },
        )
        assert response.status_code == 200
        return response.json()["result"]["structuredContent"]

    first = call_create()
    second = call_create()
    assert first["ok"] is True and first["created"] is True
    assert second["ok"] is True and second["created"] is False
    assert second["idempotent_replay"] is True
    assert first["plan"]["plan_id"] == second["plan"]["plan_id"]

    rest = client.get(
        f"/api/studio/ugc/plans/{first['plan']['plan_id']}",
        headers={"x-api-key": "u1-interface-test-key"},
    )
    assert rest.status_code == 200
    assert rest.json()["plan"] == first["plan"]
