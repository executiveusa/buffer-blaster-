"""TDD: operator auth contract.

Uses FastAPI's TestClient (in-process) so no server needs to be running.
"""
import os

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)
TEST_PASSWORD = os.environ["DEMO_PASSWORD"]


class TestDemoAuth:
    def test_admin_route_requires_token(self):
        r = client.get("/api/admin/dashboard")
        assert r.status_code == 401

    def test_wrong_password_returns_401(self):
        r = client.post("/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 401

    def test_correct_password_returns_token(self):
        r = client.post("/api/auth/verify", json={"password": TEST_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert "session_token" in data
        assert len(data["session_token"]) >= 32

    def test_token_allows_admin_access(self):
        r = client.post("/api/auth/verify", json={"password": TEST_PASSWORD})
        token = r.json()["session_token"]
        r2 = client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert "Buffer Blaster" in r2.json()["greeting"]

    def test_rate_limiting_on_auth(self):
        for _ in range(5):
            client.post("/api/auth/verify", json={"password": "wrong"})
        r = client.post("/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_password_never_logged(self, capfd):
        client.post("/api/auth/verify", json={"password": TEST_PASSWORD})
        out, err = capfd.readouterr()
        assert TEST_PASSWORD not in out
        assert TEST_PASSWORD not in err

    def test_logout_invalidates_token(self):
        r = client.post("/api/auth/verify", json={"password": TEST_PASSWORD})
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
