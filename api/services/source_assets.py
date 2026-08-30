"""Canonical source/reference assets for product shots and moodboards."""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import redis.asyncio as redis

from .asset_storage import get_asset_storage

_ZSET = "buffer_blaster:studio:source_assets:v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("BUFFER_BLASTER_WORKSPACE_ID"))


def _headers(prefer: str | None = None) -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept-Profile": "buffer_blaster", "Content-Profile": "buffer_blaster"}
    if prefer: headers["Prefer"] = prefer
    return headers


async def create_url_reference(*, url: str, kind: str = "reference", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not url.startswith("https://"):
        return {"ok": False, "error": "https_reference_required"}
    record = {"id": str(uuid.uuid4()), "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or None, "client_id": None, "kind": kind, "source_url": url, "storage_url": None, "metadata": metadata or {}, "created_at": _now()}
    return await _persist(record)


async def create_uploaded_reference(*, source: Path, filename: str, content_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    asset_id = str(uuid.uuid4())
    suffix = Path(filename).suffix.lower()[:10]
    storage = get_asset_storage()
    uploaded = await storage.upload_file(source, object_name=f"references/{asset_id}{suffix}", content_type=content_type)
    if not uploaded.get("ok"):
        return uploaded
    record = {"id": asset_id, "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or None, "client_id": None, "kind": "uploaded_reference", "source_url": None, "storage_url": uploaded.get("path"), "metadata": {**(metadata or {}), "filename": filename, "content_type": content_type}, "created_at": _now(), "signed_url": uploaded.get("signed_url")}
    persisted = await _persist(record)
    return {**persisted, "signed_url": uploaded.get("signed_url")}


async def _persist(record: dict[str, Any]) -> dict[str, Any]:
    if _supabase():
        base = os.getenv("SUPABASE_URL", "").rstrip("/")
        payload = {key: value for key, value in record.items() if key != "signed_url"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{base}/rest/v1/source_assets", headers=_headers("return=representation"), json=payload)
        if response.is_success:
            data = response.json()
            row = data[0] if isinstance(data, list) and data else payload
            return {"ok": True, "asset": row}
        return {"ok": False, "error": "source_asset_insert_failed", "status": response.status_code, "detail": response.text[:500]}
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    client = redis.from_url(url, decode_responses=True)
    try:
        await client.set(f"buffer_blaster:studio:source_asset:{record['id']}", json.dumps(record))
        await client.zadd(_ZSET, {record["id"]: time.time()})
        return {"ok": True, "asset": record}
    except redis.RedisError as exc:
        return {"ok": False, "error": "source_asset_insert_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()


async def list_references(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    if _supabase():
        base = os.getenv("SUPABASE_URL", "").rstrip("/")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base}/rest/v1/source_assets", params={"select": "*", "order": "created_at.desc", "limit": str(limit)}, headers=_headers())
        return response.json() if response.is_success and isinstance(response.json(), list) else []
    url = os.getenv("REDIS_URL", "").strip()
    if not url: return []
    client = redis.from_url(url, decode_responses=True)
    try:
        ids = await client.zrevrange(_ZSET, 0, limit - 1)
        values = await client.mget([f"buffer_blaster:studio:source_asset:{asset_id}" for asset_id in ids]) if ids else []
        out = []
        for raw in values:
            if raw:
                try: out.append(json.loads(raw))
                except json.JSONDecodeError: pass
        return out
    except redis.RedisError:
        return []
    finally:
        await client.aclose()
