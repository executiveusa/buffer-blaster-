"""Repository contract tests: demo fallback and schema-scoped Supabase access."""
from __future__ import annotations

from types import SimpleNamespace

from api.db import repositories


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.operations = []

    def select(self, *args):
        self.operations.append(("select", args))
        return self

    def order(self, *args):
        self.operations.append(("order", args))
        return self

    def eq(self, *args):
        self.operations.append(("eq", args))
        return self

    def limit(self, *args):
        self.operations.append(("limit", args))
        return self

    def insert(self, payload):
        self.operations.append(("insert", payload))
        return self

    def update(self, payload):
        self.operations.append(("update", payload))
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables
        self.queries = []

    def table(self, name):
        query = Query(self.tables.get(name, []))
        self.queries.append((name, query))
        return query


def test_client_repository_uses_platform_schema_when_configured(monkeypatch):
    """ClientRepository reads from the dedicated platform schema (postatees_stavarai),
    not from public.* — which is shared with other apps on the box."""
    fake = FakeClient({"clients": [{"slug": "brand-a", "name": "Brand A"}]})
    monkeypatch.setattr(repositories, "_platform_client", lambda: fake)

    rows = repositories.ClientRepository().list()

    assert rows[0]["slug"] == "brand-a"
    assert fake.queries[0][0] == "clients"


def test_content_repository_scopes_query_to_client_schema(monkeypatch):
    """Per-client content reads go through a schema-scoped client (namespaced
    under postatees_stavarai.schema_{slug})."""
    platform = FakeClient({"clients": [{"slug": "brand-a", "name": "Brand A"}]})
    isolated = FakeClient({"content_units": [{"id": "unit-1", "status": "pending"}]})
    monkeypatch.setattr(repositories, "_platform_client", lambda: platform)
    monkeypatch.setattr(repositories, "is_configured", lambda: True)
    monkeypatch.setattr(repositories, "_schema_client", lambda schema: isolated)

    result = repositories.ContentRepository().list_for_client("brand-a")

    schema, rows = result
    # Namespaced per-client schema name (postatees_stavarai.schema_brand_a)
    assert schema == "postatees_stavarai.schema_brand_a"
    assert rows == [
        {
            "id": "unit-1",
            "status": "pending",
            "client_slug": "brand-a",
            "schema": "postatees_stavarai.schema_brand_a",
        }
    ]
    assert isolated.queries[0][0] == "content_units"


def test_missing_client_never_queries_another_schema(monkeypatch):
    platform = FakeClient({"clients": []})
    monkeypatch.setattr(repositories, "_platform_client", lambda: platform)
    monkeypatch.setattr(repositories, "is_configured", lambda: True)

    assert repositories.ContentRepository().list_for_client("missing") is None
