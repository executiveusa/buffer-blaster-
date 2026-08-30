from fastapi.testclient import TestClient

from api.app import app


def test_voice_ugc_resolves_to_factory_plan(monkeypatch):
    monkeypatch.setenv("BLASTER_API_KEY", "voice-test-key")
    client = TestClient(app)
    response = client.post(
        "/api/voice/command",
        headers={"x-api-key": "voice-test-key"},
        json={"transcript": "make a UGC video ad for Cella Coffee", "source": "test"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "create_ugc"
    assert payload["next"] == "/api/studio/ugc/factory/plan"
