"""TDD: client data isolation contract.

Uses FastAPI's TestClient. Verifies that each client's content is tagged with
its own namespaced `schema_{slug}` and that no cross-client leakage can occur —
the contract enforced by the platform namespace migration in production.
"""
import re

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.db.client_isolation import PLATFORM_SCHEMA

client = TestClient(app)


def expected_schema(slug: str) -> str:
    return f"{PLATFORM_SCHEMA}.schema_{slug.replace('-', '_')}"


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
        assert data["schema"] == expected_schema("test-brand-a")

    def test_client_a_content_never_contains_client_b_schema(self, auth_headers):
        """Every content unit under brand-a must carry only brand-a's schema."""
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
        brand_a_schema = expected_schema("brand-a")
        assert body["schema"] == brand_a_schema
        for unit in body.get("units", []):
            assert unit["schema"] == brand_a_schema, (
                f"leak: unit {unit['id']} has schema {unit['schema']}"
            )

    def test_schema_name_sanitized(self, auth_headers):
        """A malicious slug/name must still produce a safe namespaced schema."""
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
        assert re.match(
            rf"^{re.escape(PLATFORM_SCHEMA)}\.schema_[a-z0-9_]+$",
            schema,
        )

    def test_isolation_function_directly(self):
        """Direct unit test of the sanitizer — defence in depth."""
        from api.db.client_isolation import schema_name_for

        assert schema_name_for("brand-a") == expected_schema("brand-a")
        out = schema_name_for("BRAND'A;DROP--")
        assert re.match(
            rf"^{re.escape(PLATFORM_SCHEMA)}\.schema_[a-z0-9_]+$",
            out,
        ), out
        assert "drop" in out
        assert re.match(
            rf"^{re.escape(PLATFORM_SCHEMA)}\.schema_[a-z0-9_]+$",
            schema_name_for("anything!@#$%"),
        )
