"""Persistence repositories with a safe demo fallback.

When Supabase service credentials are configured, all platform tables are
read/written through a client scoped to the dedicated platform schema
(``postatees_stavarai`` by default — see ``STAVARAI_SCHEMA`` env var and
``005_postatees_namespace.sql``). Per-client content lives under
``postatees_stavarai.schema_{slug}``. Without credentials, the in-memory demo
store remains active for local development and previews.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from .client_isolation import PLATFORM_SCHEMA, create_client_schema, schema_name_for
from .supabase_client import get_client, is_configured
from ..services import demo


def _rows(response: Any) -> list[dict]:
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    return list(data or [])


@lru_cache(maxsize=64)
def _schema_client(schema: str):
    """Create a Supabase client whose PostgREST schema is fixed to `schema`."""
    if not is_configured():
        return None
    from supabase import create_client
    from supabase.client import ClientOptions

    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
        options=ClientOptions(schema=schema),
    )


def _platform_client():
    """Client scoped to the platform schema (postatees_stavarai)."""
    return _schema_client(PLATFORM_SCHEMA)


class ClientRepository:
    def list(self) -> list[dict]:
        client = _platform_client()
        if client is None:
            return demo.list_clients()
        return _rows(client.table("clients").select("*").order("created_at").execute())

    def get(self, slug: str) -> dict | None:
        client = _platform_client()
        if client is None:
            return demo.get_client(slug)
        rows = _rows(client.table("clients").select("*").eq("slug", slug).limit(1).execute())
        if not rows:
            return None
        row = rows[0]
        row["schema"] = schema_name_for(slug)
        return row

    def create(self, *, name: str, niche: str, slug: str) -> dict:
        schema = create_client_schema(slug)
        client = _platform_client()
        if client is None:
            return demo.add_client(name=name, niche=niche, slug=slug, schema=schema)
        payload = {"name": name, "niche": niche, "slug": slug}
        rows = _rows(client.table("clients").insert(payload).execute())
        if not rows:
            raise RuntimeError("Supabase did not return the created client")
        row = rows[0]
        row["schema"] = schema
        row.setdefault("status", "active")
        row.setdefault("posts_scheduled", 0)
        row.setdefault("avg_score", 0.0)
        return row


class ContentRepository:
    def list_for_client(self, slug: str) -> tuple[str, list[dict]] | None:
        if not ClientRepository().get(slug):
            return None
        schema = schema_name_for(slug)
        client = _schema_client(schema)
        if client is None:
            return schema, demo.content_for(slug)
        rows = _rows(client.table("content_units").select("*").order("created_at").execute())
        for row in rows:
            row["client_slug"] = slug
            row["schema"] = schema
            if "score_breakdown" not in row and "score_breakdown_json" in row:
                row["score_breakdown"] = row.pop("score_breakdown_json")
        return schema, rows

    def set_status(self, unit_id: str, status: str) -> bool:
        if status not in {"approved", "rejected"}:
            raise ValueError("unsupported content status")
        if not is_configured():
            return demo.approve(unit_id) if status == "approved" else demo.reject(unit_id)

        # A content unit ID alone does not identify its client schema. Search only
        # known clients and stop after the first match; every query remains scoped
        # to one schema, preventing cross-client reads.
        for client_record in ClientRepository().list():
            slug = client_record["slug"]
            schema = schema_name_for(slug)
            client = _schema_client(schema)
            rows = _rows(
                client.table("content_units")
                .update({"status": status})
                .eq("id", unit_id)
                .select("id")
                .execute()
            )
            if rows:
                return True
        return False


clients = ClientRepository()
content = ContentRepository()
