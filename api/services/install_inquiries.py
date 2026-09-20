"""Durable install-inquiry intake with a shared Redis rate boundary."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_RATE_PREFIX = "buffer_blaster:install-inquiry-rate:v1:"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _headers(prefer: str | None = None) -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept-Profile": "buffer_blaster", "Content-Profile": "buffer_blaster"}
    if prefer:
        headers["Prefer"] = prefer
    return headers


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("BUFFER_BLASTER_WORKSPACE_ID") and os.getenv("REDIS_URL"))


async def _rate_allowed(source: str) -> bool:
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return False
    digest = hashlib.sha256(source.encode("utf-8", "ignore")).hexdigest()[:32]
    client = redis.from_url(url, decode_responses=True)
    try:
        key = f"{_RATE_PREFIX}{digest}"
        count = int(await client.incr(key))
        if count == 1:
            await client.expire(key, 3600)
        return count <= 5
    except redis.RedisError:
        return False
    finally:
        await client.aclose()


async def create_install_inquiry(*, email: str, source: str, honeypot: str = "") -> dict[str, Any]:
    if honeypot:
        return {"ok": True, "receipt_id": str(uuid.uuid4())}
    normalized = email.strip().lower()
    if len(normalized) > 320 or not _EMAIL.fullmatch(normalized):
        return {"ok": False, "error": "invalid_email"}
    if not configured():
        return {"ok": False, "error": "inquiry_store_unavailable"}
    if not await _rate_allowed(source):
        return {"ok": False, "error": "rate_limited"}
    record = {
        "id": str(uuid.uuid4()),
        "workspace_id": os.environ["BUFFER_BLASTER_WORKSPACE_ID"],
        "email": normalized,
        "status": "received",
        "created_at": _now(),
    }
    base = os.environ["SUPABASE_URL"].rstrip("/")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{base}/rest/v1/install_inquiries", headers=_headers("return=representation"), json=record)
    if not response.is_success:
        return {"ok": False, "error": "inquiry_store_failed"}
    rows = response.json()
    receipt = rows[0].get("id") if isinstance(rows, list) and rows else record["id"]
    return {"ok": True, "receipt_id": receipt}
