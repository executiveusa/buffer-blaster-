"""
TDD: Demo Auth Tests — MUST FAIL before implementation
Run: pytest 03_tests/auth/test_demo_auth.py -v
"""
import pytest
import httpx

BASE = "http://localhost:8000"

class TestDemoAuth:
    def test_admin_route_requires_password(self):
        """GET /api/admin/dashboard with no auth → 401"""
        r = httpx.get(f"{BASE}/api/admin/dashboard")
        assert r.status_code == 401

    def test_wrong_password_returns_401(self):
        """POST /api/auth/verify with wrong password → 401"""
        r = httpx.post(f"{BASE}/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 401

    def test_correct_password_returns_token(self):
        """POST /api/auth/verify with BLASTER2026 → 200 + session_token"""
        r = httpx.post(f"{BASE}/api/auth/verify", json={"password": "BLASTER2026"})
        assert r.status_code == 200
        data = r.json()
        assert "session_token" in data
        assert len(data["session_token"]) > 32

    def test_token_allows_admin_access(self):
        """Valid session_token in Authorization header → 200"""
        # First get token
        r = httpx.post(f"{BASE}/api/auth/verify", json={"password": "BLASTER2026"})
        token = r.json()["session_token"]
        # Then use it
        r2 = httpx.get(f"{BASE}/api/admin/dashboard",
                       headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

    def test_rate_limiting_on_auth(self):
        """6th attempt within 1 minute → 429"""
        for _ in range(5):
            httpx.post(f"{BASE}/api/auth/verify", json={"password": "wrong"})
        r = httpx.post(f"{BASE}/api/auth/verify", json={"password": "wrong"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_password_not_logged(self, capfd):
        """Password must never appear in stdout/stderr"""
        httpx.post(f"{BASE}/api/auth/verify", json={"password": "BLASTER2026"})
        out, err = capfd.readouterr()
        assert "BLASTER2026" not in out
        assert "BLASTER2026" not in err
