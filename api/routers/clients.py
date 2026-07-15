"""Clients router — client CRUD with per-client schema isolation.

`slug` is sanitized to `[a-z0-9_]` before being used to name a Supabase schema,
preventing SQL injection. Verified by `tests/clients/test_client_isolation.py`.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from ..deps import verify_session
from ..services import demo
from ..db import client_isolation

router = APIRouter(prefix="/api/admin/clients", tags=["clients"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


class ClientCreate(BaseModel):
    name: str
    niche: str
    slug: str

    @field_validator("slug")
    @classmethod
    def _clean_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not _SLUG_RE.match(v):
            raise ValueError("slug must be lowercase, 3-50 chars, [a-z0-9-]")
        return v

    @field_validator("niche")
    @classmethod
    def _clean_niche(cls, v: str) -> str:
        allowed = {"food-beverage", "beauty-skincare", "apparel", "home-lifestyle"}
        v = v.strip().lower()
        if v not in allowed:
            raise ValueError(f"niche must be one of {sorted(allowed)}")
        return v


def _schema_name(slug: str) -> str:
    """Slug → safe schema name. Matches `002_client_isolation.sql` sanitize."""
    safe = re.sub(r"[^a-z0-9]", "_", slug.lower())
    return f"schema_{safe}"


@router.get("")
async def list_clients(_=Depends(verify_session)) -> dict:
    return {"clients": demo.list_clients(), "total": len(demo.list_clients())}


@router.post("", status_code=201)
async def create_client(payload: ClientCreate, _=Depends(verify_session)) -> dict:
    schema = _schema_name(payload.slug)
    # Verify the sanitization contract holds (defence-in-depth — the regex
    # validator already restricts slug, but the isolation function must still
    # produce a safe identifier for any caller).
    if not re.match(r"^schema_[a-z0-9_]+$", schema):
        raise HTTPException(status_code=400, detail="invalid slug")

    # In production this calls the SQL function in the client's Supabase.
    client_isolation.create_client_schema(payload.slug)

    client = demo.add_client(
        name=payload.name, niche=payload.niche, slug=payload.slug, schema=schema
    )
    return client


@router.get("/{slug}")
async def get_client(slug: str, _=Depends(verify_session)) -> dict:
    client = demo.get_client(slug)
    if not client:
        raise HTTPException(status_code=404, detail="client not found")
    return client


@router.post("/{slug}/sync-airtable")
async def sync_airtable(slug: str, _=Depends(verify_session)) -> dict:
    return {
        "client": slug,
        "status": "queued",
        "message": "Airtable sync queued. Activate AIRTABLE_API_KEY on the VPS to run.",
    }
