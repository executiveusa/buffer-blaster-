"""Provider-neutral persistence for experiments, performance and attribution."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .experiment_engine import VariantResult, evaluate_experiment


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("BUFFER_BLASTER_WORKSPACE_ID"))


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    out = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept-Profile": "buffer_blaster",
        "Content-Profile": "buffer_blaster",
    }
    if prefer:
        out["Prefer"] = prefer
    return out


def _url(table: str) -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{table}"


async def create_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID"),
        "campaign_id": payload.get("campaign_id"),
        "name": payload["name"],
        "hypothesis": payload["hypothesis"],
        "primary_kpi": payload["primary_kpi"],
        "baseline": payload.get("baseline"),
        "pass_threshold": payload["pass_threshold"],
        "kill_threshold": payload.get("kill_threshold"),
        "attribution_window_hours": payload.get("attribution_window_hours", 168),
        "budget_ceiling_cents": payload.get("budget_ceiling_cents", 0),
        "state": "draft",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_url("experiments"), headers=_headers(prefer="return=representation"), json=record)
    if not response.is_success:
        return {"ok": False, "error": "experiment_insert_failed", "status": response.status_code}
    rows = response.json()
    return {"ok": True, "experiment": rows[0] if rows else record}


async def add_variant(experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID"),
        "experiment_id": experiment_id,
        "content_item_id": payload.get("content_item_id"),
        "role": payload["role"],
        "label": payload["label"],
        "hypothesis_delta": payload.get("hypothesis_delta", ""),
        "external_ad_refs": payload.get("external_ad_refs", {}),
        "state": payload.get("state", "draft"),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_url("experiment_variants"), headers=_headers(prefer="return=representation"), json=record)
    if not response.is_success:
        return {"ok": False, "error": "variant_insert_failed", "status": response.status_code}
    rows = response.json()
    return {"ok": True, "variant": rows[0] if rows else record}


async def bind_variant_provider_ref(variant_id: str, provider: str, external_ref: dict[str, Any]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    async with httpx.AsyncClient(timeout=10) as client:
        current = await client.get(_url("experiment_variants"), params={"id": f"eq.{variant_id}", "limit": "1"}, headers=_headers())
    if not current.is_success or not current.json():
        return {"ok": False, "error": "variant_not_found"}
    row = current.json()[0]
    refs = dict(row.get("external_ad_refs") or {})
    refs[provider] = external_ref
    patch = {"external_ad_refs": refs, "updated_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(_url("experiment_variants"), params={"id": f"eq.{variant_id}"}, headers=_headers(prefer="return=representation"), json=patch)
    rows = response.json() if response.is_success else []
    return {"ok": response.is_success, "variant": rows[0] if rows else None, "status": response.status_code}


async def ingest_performance_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Meta/TikTok/etc. metrics into the existing performance_events table."""
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID"),
        "content_item_id": payload["content_item_id"],
        "source": payload["source"],
        "metric": payload["metric"],
        "value": payload["value"],
        "observed_at": payload.get("observed_at") or _now(),
        "metadata": payload.get("metadata", {}),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_url("performance_events"), headers=_headers(prefer="return=representation"), json=record)
    return {"ok": response.is_success, "event": record, "status": response.status_code}


async def ingest_attribution_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Shopify/conversion events without embedding Shopify logic in the evaluator."""
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": os.getenv("BUFFER_BLASTER_WORKSPACE_ID"),
        "experiment_id": payload.get("experiment_id"),
        "variant_id": payload.get("variant_id"),
        "source": payload["source"],
        "event_type": payload["event_type"],
        "external_event_id": payload.get("external_event_id"),
        "revenue_cents": payload.get("revenue_cents"),
        "order_ref": payload.get("order_ref"),
        "occurred_at": payload.get("occurred_at") or _now(),
        "metadata": payload.get("metadata", {}),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_url("attribution_events"), headers=_headers(prefer="resolution=ignore-duplicates,return=representation"), json=record)
    return {"ok": response.is_success, "event": record, "status": response.status_code}


async def evaluate(experiment_id: str, variant_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("experiments"), params={"id": f"eq.{experiment_id}", "limit": "1"}, headers=_headers())
    if not response.is_success or not response.json():
        return {"ok": False, "error": "experiment_not_found"}
    exp = response.json()[0]
    decision = evaluate_experiment(
        primary_kpi=exp["primary_kpi"],
        pass_threshold=float(exp["pass_threshold"]),
        kill_threshold=float(exp["kill_threshold"]) if exp.get("kill_threshold") is not None else None,
        variants=[VariantResult(**row) for row in variant_results],
        higher_is_better=bool(exp.get("decision", {}).get("higher_is_better", True)),
        minimum_sample_size=int(exp.get("decision", {}).get("minimum_sample_size", 1)),
    )
    patch = {"decision": decision, "updated_at": _now()}
    if decision["status"] == "PASS":
        patch.update({"state": "passed", "winner_variant_id": decision["winner_variant_id"]})
    elif decision["status"] == "KILL":
        patch["state"] = "killed"
    elif decision["status"] == "ITERATE":
        patch["state"] = "iterate"
    async with httpx.AsyncClient(timeout=10) as client:
        updated = await client.patch(_url("experiments"), params={"id": f"eq.{experiment_id}"}, headers=_headers(prefer="return=representation"), json=patch)
    return {"ok": updated.is_success, "experiment_id": experiment_id, "decision": decision}
