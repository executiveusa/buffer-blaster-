"""TDD: demo auth contract.

Uses FastAPI's TestClient (in-process) so no server needs to be running.
Mirrors docs/TDD_SPEC.md SPEC 1.1 + 1.3.
"""
import pytest
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


class TestDemoAuth:
    def test_admin_route_requires_token(self):
        """GET /api/admin/dashboard with no auth → 401."""
        r = client.get("/api/admin/dashboard")
        assert r.status_code == 401

    def test_wrong_password_returns_401(self):
        r = client.post("/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 401

    def test_correct_password_returns_token(self):
        r = client.post("/api/auth/verify", json={"password": "BLASTER2026"})
        assert r.status_code == 200
        data = r.json()
        assert "session_token" in data
        assert len(data["session_token"]) >= 32

    def test_token_allows_admin_access(self):
        r = client.post("/api/auth/verify", json={"password": "BLASTER2026"})
        token = r.json()["session_token"]
        r2 = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert "Stavarai" in r2.json()["greeting"]

    def test_rate_limiting_on_auth(self):
        """6th attempt within a minute → 429 + Retry-After header."""
        for _ in range(5):
            client.post("/api/auth/verify", json={"password": "wrong"})
        r = client.post("/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_password_never_logged(self, capfd):
        """The password must not appear in captured stdout/stderr."""
        client.post("/api/auth/verify", json={"password": "BLASTER2026"})
        out, err = capfd.readouterr()
        assert "BLASTER2026" not in out
        assert "BLASTER2026" not in err

    def test_logout_invalidates_token(self):
        r = client.post("/api/auth/verify", json={"password": "BLASTER2026"})
        token = r.json()["session_token"]
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        r2 = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 401

    def test_health_reports_core_backend(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["core"] in ("rust", "python")
