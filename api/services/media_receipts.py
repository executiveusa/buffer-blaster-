"""Canonical persistence for provider-neutral media receipts.

Self-hosted Supabase is authoritative when configured. Redis is a truthful
persistent degraded fallback during self-host bring-up. These functions never
invoke generation providers or reserve spend.
"""
from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

import httpx
import redis.asyncio as redis

from .media_contracts import UGCPlan, UGCPlanDraft


_REDIS_PLAN_PREFIX = "buffer_blaster:ugc:plan:v1"
_REDIS_IDEMPOTENCY_PREFIX = "buffer_blaster:ugc:plan:idempotency:v1"


def _workspace_id() -> UUID:
    raw = (os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or "").strip()
    if not raw:
        raise RuntimeError("BUFFER_BLASTER_WORKSPACE_ID is required")
    try:
        return UUID(raw)
    except ValueError as exc:
        raise RuntimeError("BUFFER_BLASTER_WORKSPACE_ID must be a UUID") from exc


def _supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("BUFFER_BLASTER_WORKSPACE_ID"))


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
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    return redis.from_url(url, decode_responses=True)


def receipt_backend_status() -> dict[str, Any]:
    if _supabase_configured():
        return {"backend": "supabase", "persistent": True, "canonical": True}
    if os.getenv("REDIS_URL"):
        return {"backend": "redis", "persistent": True, "canonical": False, "degraded_from": "supabase"}
    return {"backend": "unavailable", "persistent": False, "canonical": False}


def _workspace_error() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "canonical_workspace_not_configured",
        "paid_generation": False,
        "backend": "unavailable",
    }


async def _get_supabase_plan_by_idempotency(workspace_id: UUID, idempotency_key: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            _table_url("ugc_plans"),
            params={
                "workspace_id": f"eq.{workspace_id}",
                "idempotency_key": f"eq.{idempotency_key}",
                "limit": "1",
            },
            headers=_headers(),
        )
    if not response.is_success:
        return None
    data = response.json()
    return data[0] if isinstance(data, list) and data else None


async def create_ugc_plan(draft: UGCPlanDraft) -> dict[str, Any]:
    """Persist one no-spend UGC plan with workspace-scoped idempotency."""
    try:
        workspace_id = _workspace_id()
    except RuntimeError:
        return _workspace_error()
    record = UGCPlan(workspace_id=workspace_id, **draft.model_dump()).model_dump(mode="json")

    if _supabase_configured():
        existing = await _get_supabase_plan_by_idempotency(workspace_id, draft.idempotency_key)
        if existing:
            return {
                "ok": True,
                "plan": existing,
                "created": False,
                "idempotent_replay": True,
                "paid_generation": False,
                "backend": "supabase",
            }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _table_url("ugc_plans"),
                headers=_headers(prefer="return=representation"),
                json=record,
            )
        if response.is_success:
            data = response.json()
            persisted = data[0] if isinstance(data, list) and data else record
            return {
                "ok": True,
                "plan": persisted,
                "created": True,
                "idempotent_replay": False,
                "paid_generation": False,
                "backend": "supabase",
            }

        # A concurrent request may have won the unique idempotency constraint.
        if response.status_code == 409:
            existing = await _get_supabase_plan_by_idempotency(workspace_id, draft.idempotency_key)
            if existing:
                return {
                    "ok": True,
                    "plan": existing,
                    "created": False,
                    "idempotent_replay": True,
                    "paid_generation": False,
                    "backend": "supabase",
                }
        return {
            "ok": False,
            "error": "ugc_plan_persistence_failed",
            "status": response.status_code,
            "paid_generation": False,
            "backend": "supabase",
        }

    client = await _redis_client()
    if client is None:
        return {
            "ok": False,
            "error": "canonical_receipt_store_unavailable",
            "paid_generation": False,
            "backend": "unavailable",
        }

    idempotency_key = f"{_REDIS_IDEMPOTENCY_PREFIX}:{workspace_id}:{draft.idempotency_key}"
    plan_key = f"{_REDIS_PLAN_PREFIX}:{workspace_id}:{record['plan_id']}"
    raw = json.dumps(record, separators=(",", ":"))
    try:
        inserted = await client.set(idempotency_key, raw, nx=True)
        if not inserted:
            existing_raw = await client.get(idempotency_key)
            if existing_raw:
                existing = json.loads(existing_raw)
                existing_plan_id = existing.get("plan_id")
                if existing_plan_id:
                    # Repair the secondary lookup if a prior process died after
                    # the idempotency write but before writing the plan key.
                    await client.set(f"{_REDIS_PLAN_PREFIX}:{workspace_id}:{existing_plan_id}", existing_raw)
                return {
                    "ok": True,
                    "plan": existing,
                    "created": False,
                    "idempotent_replay": True,
                    "paid_generation": False,
                    "backend": "redis",
                }
            return {"ok": False, "error": "redis_idempotency_read_failed", "paid_generation": False, "backend": "redis"}
        await client.set(plan_key, raw)
        return {
            "ok": True,
            "plan": record,
            "created": True,
            "idempotent_replay": False,
            "paid_generation": False,
            "backend": "redis",
        }
    except (redis.RedisError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error": "redis_ugc_plan_failed",
            "detail": type(exc).__name__,
            "paid_generation": False,
            "backend": "redis",
        }
    finally:
        await client.aclose()


async def get_ugc_plan(plan_id: str | UUID) -> dict[str, Any]:
    """Read one plan only inside the configured workspace boundary."""
    try:
        workspace_id = _workspace_id()
    except RuntimeError:
        return {**_workspace_error(), "plan": None}
    try:
        normalized_plan_id = UUID(str(plan_id))
    except ValueError:
        return {"ok": False, "error": "invalid_plan_id", "plan": None, "paid_generation": False}

    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _table_url("ugc_plans"),
                params={
                    "plan_id": f"eq.{normalized_plan_id}",
                    "workspace_id": f"eq.{workspace_id}",
                    "limit": "1",
                },
                headers=_headers(),
            )
        if not response.is_success:
            return {"ok": False, "error": "ugc_plan_read_failed", "plan": None, "status": response.status_code, "paid_generation": False}
        data = response.json()
        row = data[0] if isinstance(data, list) and data else None
        return {"ok": bool(row), "plan": row, "error": None if row else "ugc_plan_not_found", "paid_generation": False, "backend": "supabase"}

    client = await _redis_client()
    if client is None:
        return {"ok": False, "error": "canonical_receipt_store_unavailable", "plan": None, "paid_generation": False, "backend": "unavailable"}
    try:
        raw = await client.get(f"{_REDIS_PLAN_PREFIX}:{workspace_id}:{normalized_plan_id}")
        row = json.loads(raw) if raw else None
        return {"ok": bool(row), "plan": row, "error": None if row else "ugc_plan_not_found", "paid_generation": False, "backend": "redis"}
    except (redis.RedisError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": "redis_ugc_plan_read_failed", "detail": type(exc).__name__, "plan": None, "paid_generation": False, "backend": "redis"}
    finally:
        await client.aclose()
