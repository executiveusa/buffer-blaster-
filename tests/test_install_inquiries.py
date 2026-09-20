import os

from fastapi.testclient import TestClient

from api.app import app


def test_install_inquiry_rejects_invalid_email(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://unused")
    monkeypatch.setenv("SUPABASE_URL", "http://unused")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "unused")
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "00000000-0000-0000-0000-000000000001")
    response = TestClient(app).post("/api/install-inquiries", json={"email": "not-an-email"})
    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "invalid_email"}


def test_install_inquiry_honeypot_does_not_persist(monkeypatch):
    for key in ("REDIS_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "BUFFER_BLASTER_WORKSPACE_ID"):
        monkeypatch.delenv(key, raising=False)
    response = TestClient(app).post("/api/install-inquiries", json={"email": "bot@example.com", "bot_field": "filled"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["receipt_id"]


def test_install_inquiry_fails_closed_without_store(monkeypatch):
    for key in ("REDIS_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "BUFFER_BLASTER_WORKSPACE_ID"):
        monkeypatch.delenv(key, raising=False)
    response = TestClient(app).post("/api/install-inquiries", json={"email": "person@example.com"})
    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "inquiry_store_unavailable"}
