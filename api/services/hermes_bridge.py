"""Durable, retry-safe receipts for Hermes <-> Buffer Blaster handoffs."""
from __future__ import annotations

import os
import uuid
from typing import Any

import httpx


def _workspace_id() -> str:
    return os.getenv("BUFFER_BLASTER_WORKSPACE_ID", "").strip()


def _configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and _workspace_id())


def _url(table: str) -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{table}"


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


def experiment_id_for(correlation_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"buffer-blaster:hermes:{correlation_id}"))


def receipt_id_for(correlation_id: str, stage: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"buffer-blaster:hermes:{correlation_id}:{stage}"))


async def get_experiment(experiment_id: str) -> dict[str, Any] | None:
    if not _configured():
        return None
    params = {
        "workspace_id": f"eq.{_workspace_id()}",
        "id": f"eq.{experiment_id}",
        "select": "*",
        "limit": "1",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("experiments"), params=params, headers=_headers())
    rows = response.json() if response.is_success else []
    return rows[0] if isinstance(rows, list) and rows else None


async def record_receipt(
    *,
    experiment_id: str | None,
    correlation_id: str,
    stage: str,
    status: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    record = {
        "id": receipt_id_for(correlation_id, stage),
        "workspace_id": _workspace_id(),
        "experiment_id": experiment_id,
        "stage": stage,
        "status": status,
        "evidence": {"correlation_id": correlation_id, **(evidence or {})},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            _url("money_loop_receipts"),
            headers=_headers(prefer="resolution=ignore-duplicates,return=representation"),
            json=record,
        )
    if not response.is_success:
        return {"ok": False, "error": "receipt_insert_failed", "status": response.status_code}
    rows = response.json() if response.content else []
    if rows:
        return {"ok": True, "receipt": rows[0], "idempotent": False}
    # Duplicate primary key: read back the canonical receipt rather than fabricating success evidence.
    params = {
        "workspace_id": f"eq.{_workspace_id()}",
        "id": f"eq.{record['id']}",
        "select": "*",
        "limit": "1",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        current = await client.get(_url("money_loop_receipts"), params=params, headers=_headers())
    current_rows = current.json() if current.is_success else []
    return {
        "ok": bool(current_rows),
        "receipt": current_rows[0] if current_rows else None,
        "idempotent": bool(current_rows),
    }


async def list_receipts(experiment_id: str, correlation_id: str | None = None) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    params: dict[str, str] = {
        "workspace_id": f"eq.{_workspace_id()}",
        "experiment_id": f"eq.{experiment_id}",
        "select": "id,experiment_id,stage,status,evidence,created_at",
        "order": "created_at.asc",
    }
    if correlation_id:
        params["evidence->>correlation_id"] = f"eq.{correlation_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("money_loop_receipts"), params=params, headers=_headers())
    if not response.is_success:
        return {"ok": False, "error": "receipt_read_failed", "status": response.status_code}
    return {"ok": True, "receipts": response.json()}
