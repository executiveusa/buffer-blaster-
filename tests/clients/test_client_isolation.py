"""
TDD: Client Data Isolation Tests — MUST FAIL before implementation
"""
import pytest
import httpx

BASE = "http://localhost:8000"
HEADERS = {}  # populated by fixture

@pytest.fixture(autouse=True)
def auth(requests_mock):
    r = httpx.post(f"{BASE}/api/auth/verify", json={"password": "BLASTER2026"})
    HEADERS["Authorization"] = f"Bearer {r.json()['session_token']}"

class TestClientIsolation:
    def test_create_client_creates_schema(self):
        """POST /api/admin/clients → creates schema_{slug} in Supabase"""
        r = httpx.post(f"{BASE}/api/admin/clients",
                      json={"name": "Test Brand A", "niche": "food-beverage", "slug": "test-brand-a"},
                      headers=HEADERS)
        assert r.status_code == 201
        data = r.json()
        assert data["slug"] == "test-brand-a"
        assert data["schema"] == "schema_test_brand_a"

    def test_client_a_cannot_read_client_b_data(self):
        """Query for client A with client B's schema → empty / 404"""
        # Create two clients
        httpx.post(f"{BASE}/api/admin/clients",
                  json={"name": "Brand A", "niche": "food-beverage", "slug": "brand-a"},
                  headers=HEADERS)
        httpx.post(f"{BASE}/api/admin/clients",
                  json={"name": "Brand B", "niche": "beauty-skincare", "slug": "brand-b"},
                  headers=HEADERS)
        # Get Brand A's content — should not include Brand B's rows
        r = httpx.get(f"{BASE}/api/admin/content/brand-a", headers=HEADERS)
        assert r.status_code == 200
        for unit in r.json().get("content_units", []):
            assert unit.get("schema") == "schema_brand_a"

    def test_schema_name_sanitized(self):
        """Slug with special chars → safely sanitized schema name"""
        r = httpx.post(f"{BASE}/api/admin/clients",
                      json={"name": "Brand 'DROP SCHEMA--", "niche": "apparel",
                            "slug": "safe-brand"},
                      headers=HEADERS)
        assert r.status_code == 201
        # Schema name must be alphanumeric + underscores only
        schema = r.json()["schema"]
        import re
        assert re.match(r'^schema_[a-z0-9_]+$', schema)
