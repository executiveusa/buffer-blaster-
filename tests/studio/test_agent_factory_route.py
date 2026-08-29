from fastapi.testclient import TestClient

from api.app import app


def test_live_agent_ugc_command_routes_to_factory_plan(monkeypatch):
    monkeypatch.setenv("BLASTER_API_KEY", "test-agent-key")
    client = TestClient(app)

    response = client.post(
        "/api/studio/agent/command",
        headers={"x-api-key": "test-agent-key"},
        json={"command": "make a UGC video ad for this product"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "create_ugc"
    assert payload["requires_approval"] is False
    assert payload["next"] == "/api/studio/ugc/factory/plan"
