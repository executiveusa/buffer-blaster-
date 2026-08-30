"""Canonical production ledger for Social Studio campaigns and creative jobs.

Supabase `buffer_blaster` is primary when a workspace is configured. Redis is a
truthful durable fallback for self-host bring-up; demo state is never used here.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis


_REDIS_JOBS_ZSET = "buffer_blaster:studio:jobs:v1"
_REDIS_CAMPAIGNS_ZSET = "buffer_blaster:studio:campaigns:v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL")
        and os.getenv("SUPABASE_SERVICE_KEY")
        and os.getenv("BUFFER_BLASTER_WORKSPACE_ID")
    )


def backend_status() -> dict[str, Any]:
    if _supabase_configured():
        return {"backend": "supabase", "persistent": True, "canonical": True}
    if os.getenv("REDIS_URL"):
        return {"backend": "redis", "persistent": True, "canonical": True, "degraded_from": "supabase"}
    return {"backend": "unavailable", "persistent": False, "canonical": False}


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": "buffer_blaster",
        "Content-Profile": "buffer_blaster",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _table_url(table: str) -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{table}"


async def _redis_client():
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    return redis.from_url(url, decode_responses=True)


async def create_job(
    *,
    kind: str,
    state: str,
    input_payload: dict[str, Any],
    provider_receipt: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    estimated_provider_cost_cents: int = 0,
    offer_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "id": job_id or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or None,
        "kind": kind,
        "state": state,
        "input": input_payload,
        "output": output_payload or {},
        "provider_receipt": provider_receipt or {},
        "estimated_provider_cost_cents": max(0, int(estimated_provider_cost_cents)),
        "actual_provider_cost_cents": None,
        "offer_id": offer_id,
        "created_at": _now(),
        "updated_at": _now(),
    }

    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _table_url("creative_jobs"),
                headers=_headers(prefer="return=representation"),
                json=record,
            )
        if response.is_success:
            data = response.json()
            return data[0] if isinstance(data, list) and data else record
        return {**record, "ledger_error": "supabase_insert_failed", "ledger_status": response.status_code}

    client = await _redis_client()
    if client is None:
        return {**record, "ledger_error": "canonical_ledger_unavailable"}
    try:
        await client.set(f"buffer_blaster:studio:job:{record['id']}", json.dumps(record))
        await client.zadd(_REDIS_JOBS_ZSET, {record["id"]: time.time()})
    except redis.RedisError as exc:
        return {**record, "ledger_error": "redis_insert_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()
    return record


async def update_job(job_id: str, **changes: Any) -> dict[str, Any] | None:
    changes = {**changes, "updated_at": _now()}
    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.patch(
                _table_url("creative_jobs"),
                params={"id": f"eq.{job_id}"},
                headers=_headers(prefer="return=representation"),
                json=changes,
            )
        if response.is_success:
            data = response.json()
            return data[0] if isinstance(data, list) and data else None
        return None

    client = await _redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(f"buffer_blaster:studio:job:{job_id}")
        if not raw:
            return None
        record = json.loads(raw)
        record.update(changes)
        await client.set(f"buffer_blaster:studio:job:{job_id}", json.dumps(record))
        return record
    except (redis.RedisError, json.JSONDecodeError):
        return None
    finally:
        await client.aclose()


async def get_job(job_id: str) -> dict[str, Any] | None:
    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _table_url("creative_jobs"),
                params={"id": f"eq.{job_id}", "limit": "1"},
                headers=_headers(),
            )
        if response.is_success:
            data = response.json()
            return data[0] if isinstance(data, list) and data else None
        return None

    client = await _redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(f"buffer_blaster:studio:job:{job_id}")
        return json.loads(raw) if raw else None
    except (redis.RedisError, json.JSONDecodeError):
        return None
    finally:
        await client.aclose()


async def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _table_url("creative_jobs"),
                params={"select": "*", "order": "created_at.desc", "limit": str(limit)},
                headers=_headers(),
            )
        return response.json() if response.is_success and isinstance(response.json(), list) else []

    client = await _redis_client()
    if client is None:
        return []
    records: list[dict[str, Any]] = []
    try:
        ids = await client.zrevrange(_REDIS_JOBS_ZSET, 0, limit - 1)
        if not ids:
            return []
        values = await client.mget([f"buffer_blaster:studio:job:{job_id}" for job_id in ids])
        for raw in values:
            if raw:
                try:
                    records.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        return records
    except redis.RedisError:
        return []
    finally:
        await client.aclose()


async def create_campaign(plan: dict[str, Any]) -> dict[str, Any]:
    record = {
        "id": plan.get("id") or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or None,
        "brand": plan.get("brand", ""),
        "objective": plan.get("objective", ""),
        "audience": plan.get("audience", ""),
        "offer": plan.get("offer", ""),
        "state": "draft",
        "plan": plan,
        "created_at": _now(),
        "updated_at": _now(),
    }
    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _table_url("campaigns"),
                headers=_headers(prefer="return=representation"),
                json=record,
            )
        if response.is_success:
            data = response.json()
            return data[0] if isinstance(data, list) and data else record
        return {**record, "ledger_error": "supabase_insert_failed", "ledger_status": response.status_code}

    client = await _redis_client()
    if client is None:
        return {**record, "ledger_error": "canonical_ledger_unavailable"}
    try:
        await client.set(f"buffer_blaster:studio:campaign:{record['id']}", json.dumps(record))
        await client.zadd(_REDIS_CAMPAIGNS_ZSET, {record["id"]: time.time()})
    except redis.RedisError as exc:
        return {**record, "ledger_error": "redis_insert_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()
    return record


async def summary() -> dict[str, Any]:
    jobs = await list_jobs(200)
    campaigns = 0
    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _table_url("campaigns"),
                params={"select": "id"},
                headers={**_headers(), "Prefer": "count=exact"},
            )
        if response.is_success:
            content_range = response.headers.get("content-range", "")
            if "/" in content_range:
                try:
                    campaigns = int(content_range.rsplit("/", 1)[-1])
                except ValueError:
                    campaigns = len(response.json()) if isinstance(response.json(), list) else 0
    else:
        client = await _redis_client()
        if client is not None:
            try:
                campaigns = int(await client.zcard(_REDIS_CAMPAIGNS_ZSET))
            except redis.RedisError:
                campaigns = 0
            finally:
                await client.aclose()

    states: dict[str, int] = {}
    for job in jobs:
        state = str(job.get("state") or "unknown")
        states[state] = states.get(state, 0) + 1
    completed = sum(count for state, count in states.items() if state in {"finished", "delivered", "qa_passed"})
    active = sum(count for state, count in states.items() if state in {"planned", "render_queued", "rendering", "processing", "stitching"})
    failed = sum(count for state, count in states.items() if "fail" in state or state == "error")
    return {
        "ok": backend_status()["canonical"],
        "ledger": backend_status(),
        "campaigns": campaigns,
        "jobs_total": len(jobs),
        "jobs_active": active,
        "jobs_completed": completed,
        "jobs_failed": failed,
        "states": states,
    }
