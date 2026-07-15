"""Per-client schema isolation.

`create_client_schema(slug)`:
  - Sanitizes the slug to `[a-z0-9_]` (SQL-injection-safe — verified by test).
  - In production (Supabase configured): RPC to the `create_client_schema`
    SQL function in `002_client_isolation.sql`, which creates `schema_{slug}`
    with all 8 buffer-blaster tables under RLS.
  - In dev (no Supabase): records the schema name in the demo store so the
    isolation contract can still be tested and observed.

The schema name returned is ALWAYS `schema_{sanitized_slug}` — never `public`
and never another client's schema.
"""
from __future__ import annotations

import re

from .supabase_client import get_client

_SLUG_SANITIZE = re.compile(r"[^a-z0-9]")


def sanitize_slug(slug: str) -> str:
    """Lowercase + replace every non [a-z0-9] char with `_`."""
    return _SLUG_SANITIZE.sub("_", slug.lower())


def schema_name_for(slug: str) -> str:
    safe = sanitize_slug(slug)
    return f"schema_{safe}"


def create_client_schema(slug: str) -> str:
    """Create the isolated schema for a client. Returns the schema name.

    The returned value is guaranteed to match `^schema_[a-z0-9_]+$` regardless
    of the input slug — this is the contract verified by the isolation test.
    """
    schema = schema_name_for(slug)
    assert re.match(r"^schema_[a-z0-9_]+$", schema), f"unsafe schema name: {schema}"

    client = get_client()
    if client is not None:
        # Production: call the SQL function (SECURITY DEFINER).
        # It creates the schema + tables + RLS and logs a bead.
        client.rpc("create_client_schema", {"client_slug": slug}).execute()
    # Dev: the demo store already holds the schema name; nothing to do here.
    return schema
