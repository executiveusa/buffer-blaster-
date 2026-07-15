"""TDD: client data isolation contract.

Uses FastAPI's TestClient. Verifies that each client's content is tagged with
its own `schema_{slug}` and that no cross-client leakage can occur — the
contract enforced by `002_client_isolation.sql` in production.
"""
import re

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services import demo

client = TestClient(app)


@pytest.fixture(autouse=True)
def auth_headers():
    r = client.post("/api/auth/verify", json={"password": "BLASTER2026"})
    assert r.status_code == 200
    token = r.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


class TestClientIsolation:
    def test_create_client_creates_schema(self, auth_headers):
        r = client.post(
            "/api/admin/clients",
            json={
                "name": "Test Brand A",
                "niche": "food-beverage",
                "slug": "test-brand-a",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["slug"] == "test-brand-a"
        assert data["schema"] == "schema_test_brand_a"

    def test_client_a_content_never_contains_client_b_schema(self, auth_headers):
        """Every content unit under brand-a must carry schema_brand_a only."""
        # Seed two clients (demo already has cella-coffee + lumen-skincare,
        # but we add explicit ones to be deterministic).
        client.post(
            "/api/admin/clients",
            json={"name": "Brand A", "niche": "food-beverage", "slug": "brand-a"},
            headers=auth_headers,
        )
        client.post(
            "/api/admin/clients",
            json={"name": "Brand B", "niche": "beauty-skincare", "slug": "brand-b"},
            headers=auth_headers,
        )
        r = client.get("/api/admin/content/brand-a", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["schema"] == "schema_brand_a"
        for unit in body.get("units", []):
            assert unit["schema"] == "schema_brand_a", (
                f"leak: unit {unit['id']} has schema {unit['schema']}"
            )

    def test_schema_name_sanitized(self, auth_headers):
        """A malicious slug/name must still produce a safe schema name."""
        r = client.post(
            "/api/admin/clients",
            json={
                "name": "Brand 'DROP SCHEMA--",
                "niche": "apparel",
                "slug": "safe-brand",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        schema = r.json()["schema"]
        assert re.match(r"^schema_[a-z0-9_]+$", schema)

    def test_isolation_function_directly(self):
        """Direct unit test of the sanitizer — defence in depth."""
        from api.db.client_isolation import schema_name_for

        assert schema_name_for("brand-a") == "schema_brand_a"
        # Every non [a-z0-9] char → '_'. The sanitizer must still produce a
        # name matching ^schema_[a-z0-9_]+$ regardless of input.
        out = schema_name_for("BRAND'A;DROP--")
        assert re.match(r"^schema_[a-z0-9_]+$", out), out
        assert "drop" in out
        assert re.match(r"^schema_[a-z0-9_]+$", schema_name_for("anything!@#$%"))
