"""Supabase client — lazily created when SUPABASE_URL is set.

In dev/demo (no env), `get_client()` returns None and the app serves seeded
data from `services.demo`. On the VPS, set SUPABASE_URL + SUPABASE_SERVICE_KEY
and the real client takes over.
"""
from __future__ import annotations

import os

_client = None
_tried = False


def get_client():
    """Return a Supabase client, or None if not configured (dev mode)."""
    global _client, _tried
    if _tried:
        return _client
    _tried = True
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
    except Exception:
        _client = None
    return _client


def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))
