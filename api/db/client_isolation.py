"""Per-client schema isolation.

Postatees deployment: ALL platform tables live under a dedicated
`postatees_stavarai` schema (see 005_postatees_namespace.sql). This isolates
the platform from other apps sharing the same Supabase instance (notably
cascadia-brain, which has its own clients/agent_logs/etc. in public.*).

Per-client data schemas (one schema per onboarded client) live UNDER the
platform schema as `postatees_stavarai.schema_{slug}` — see
`postatees_stavarai.create_client_schema()` in 005_postatees_namespace.sql.
"""
from __future__ import annotations

import os
import re

from .supabase_client import get_client

# Dedicated namespace for this platform. Override via env for non-Postatees deploys.
PLATFORM_SCHEMA = os.getenv("STAVARAI_SCHEMA", "postatees_stavarai")

_SLUG_SANITIZE = re.compile(r"[^a-z0-9]")


def sanitize_slug(slug: str) -> str:
    """Lowercase + replace every non [a-z0-9] char with `_`."""
    return _SLUG_SANITIZE.sub("_", slug.lower())


def schema_name_for(slug: str) -> str:
    """Per-client schema name, namespaced under the platform schema.

    Returns e.g. `postatees_stavarai.schema_cella_coffee`. This is what every
    client-scoped query uses — never `public.*` and never another client's schema.
    """
    safe = sanitize_slug(slug)
    return f"{PLATFORM_SCHEMA}.schema_{safe}"


def create_client_schema(slug: str) -> str:
    """Create the isolated schema for a client. Returns the schema name.

    Calls the Postatees-namespaced `postatees_stavarai.create_client_schema()`
    function (defined in 005_postatees_namespace.sql). The function itself
    enforces the safe-name contract; we double-check here as defence in depth.
    """
    schema = schema_name_for(slug)
    # Defence in depth: the name must match our safe pattern.
    assert re.match(rf"^{re.escape(PLATFORM_SCHEMA)}\.schema_[a-z0-9_]+$", schema), \
        f"unsafe schema name: {schema}"

    client = get_client()
    if client is not None:
        # RPC to the namespaced function.
        client.rpc(
            f"{PLATFORM_SCHEMA}.create_client_schema",
            {"client_slug": slug},
        ).execute()
    return schema
