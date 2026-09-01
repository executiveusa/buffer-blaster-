"""Provider-neutral persistence for experiments, performance and attribution."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .experiment_engine import VariantResult, evaluate_experiment

PAID_MEDIA_PROVIDERS = {"meta", "tiktok"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _workspace_id() -> str:
    return os.getenv("BUFFER_BLASTER_WORKSPACE_ID", "").strip()


def _configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and _workspace_id())


def _scoped_params(params: dict[str, str] | None = None) -> dict[str, str]:
    """PostgREST params for service-role access, which bypasses RLS."""
    scoped = {"workspace_id": f"eq.{_workspace_id()}"}
    if params:
        scoped.update(params)
    return scoped


def _paid_provider_names(refs: dict[str, Any]) -> set[str]:
    """Return paid-media providers bound inside an external_ad_refs object."""
    names = {name for name in PAID_MEDIA_PROVIDERS if isinstance(refs.get(name), dict)}
    provider = refs.get("provider")
    if provider in PAID_MEDIA_PROVIDERS:
        names.add(str(provider))
    return names


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


async def _row_exists(table: str, row_id: str, *, extra: dict[str, str] | None = None) -> bool:
    if not _configured() or not row_id:
        return False
    params = _scoped_params({"id": f"eq.{row_id}", "select": "id", "limit": "1"})
    if extra:
        params.update(extra)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url(table), params=params, headers=_headers())
    rows = response.json() if response.is_success else []
    return bool(isinstance(rows, list) and rows)


async def create_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    campaign_id = payload.get("campaign_id")
    if campaign_id and not await _row_exists("campaigns", str(campaign_id)):
        return {"ok": False, "error": "campaign_not_found_in_workspace"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": _workspace_id(),
        "campaign_id": campaign_id,
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
    if not await _row_exists("experiments", experiment_id):
        return {"ok": False, "error": "experiment_not_found_in_workspace"}
    content_item_id = payload.get("content_item_id")
    if content_item_id and not await _row_exists("content_items", str(content_item_id)):
        return {"ok": False, "error": "content_item_not_found_in_workspace"}
    refs = dict(payload.get("external_ad_refs") or {})
    providers = _paid_provider_names(refs)
    if len(providers) > 1:
        return {"ok": False, "error": "one_paid_provider_per_variant", "providers": sorted(providers)}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": _workspace_id(),
        "experiment_id": experiment_id,
        "content_item_id": content_item_id,
        "role": payload["role"],
        "label": payload["label"],
        "hypothesis_delta": payload.get("hypothesis_delta", ""),
        "external_ad_refs": refs,
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
    if provider not in PAID_MEDIA_PROVIDERS:
        return {"ok": False, "error": "unsupported_paid_media_provider"}
    async with httpx.AsyncClient(timeout=10) as client:
        current = await client.get(
            _url("experiment_variants"),
            params=_scoped_params({"id": f"eq.{variant_id}", "limit": "1"}),
            headers=_headers(),
        )
    if not current.is_success or not current.json():
        return {"ok": False, "error": "variant_not_found_in_workspace"}
    row = current.json()[0]
    refs = dict(row.get("external_ad_refs") or {})
    existing = _paid_provider_names(refs) - {provider}
    if existing:
        return {
            "ok": False,
            "error": "one_paid_provider_per_variant",
            "existing_provider": sorted(existing)[0],
            "requested_provider": provider,
        }
    refs[provider] = external_ref
    patch = {"external_ad_refs": refs, "updated_at": _now()}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            _url("experiment_variants"),
            params=_scoped_params({"id": f"eq.{variant_id}"}),
            headers=_headers(prefer="return=representation"),
            json=patch,
        )
    rows = response.json() if response.is_success else []
    return {"ok": response.is_success, "variant": rows[0] if rows else None, "status": response.status_code}


async def ingest_performance_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize Meta/TikTok/etc. metrics into the existing performance_events table."""
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    content_item_id = str(payload["content_item_id"])
    if not await _row_exists("content_items", content_item_id):
        return {"ok": False, "error": "content_item_not_found_in_workspace"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": _workspace_id(),
        "content_item_id": content_item_id,
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
    experiment_id = payload.get("experiment_id")
    variant_id = payload.get("variant_id")
    if experiment_id and not await _row_exists("experiments", str(experiment_id)):
        return {"ok": False, "error": "experiment_not_found_in_workspace"}
    if variant_id:
        extra = {"experiment_id": f"eq.{experiment_id}"} if experiment_id else None
        if not await _row_exists("experiment_variants", str(variant_id), extra=extra):
            return {"ok": False, "error": "variant_not_found_in_workspace"}
    record = {
        "id": payload.get("id") or str(uuid.uuid4()),
        "workspace_id": _workspace_id(),
        "experiment_id": experiment_id,
        "variant_id": variant_id,
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


async def find_order_attribution(order_ref: str) -> dict[str, Any] | None:
    """Resolve later Shopify lifecycle/transaction events to the original paid order."""
    if not _configured() or not order_ref:
        return None
    params = _scoped_params({
        "source": "eq.shopify",
        "order_ref": f"eq.{order_ref}",
        "event_type": "eq.orders.paid",
        "experiment_id": "not.is.null",
        "variant_id": "not.is.null",
        "select": "experiment_id,variant_id,order_ref,metadata",
        "order": "occurred_at.asc",
        "limit": "1",
    })
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("attribution_events"), params=params, headers=_headers())
    rows = response.json() if response.is_success else []
    return rows[0] if isinstance(rows, list) and rows else None


async def evaluate(experiment_id: str, variant_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not _configured():
        return {"ok": False, "error": "canonical_ledger_unavailable"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            _url("experiments"),
            params=_scoped_params({"id": f"eq.{experiment_id}", "limit": "1"}),
            headers=_headers(),
        )
    if not response.is_success or not response.json():
        return {"ok": False, "error": "experiment_not_found_in_workspace"}
    exp = response.json()[0]

    seen: set[str] = set()
    for row in variant_results:
        variant_id = str(row.get("variant_id") or "")
        if not variant_id or variant_id in seen:
            return {"ok": False, "error": "invalid_or_duplicate_variant_result"}
        seen.add(variant_id)
        if not await _row_exists("experiment_variants", variant_id, extra={"experiment_id": f"eq.{experiment_id}"}):
            return {"ok": False, "error": "variant_not_found_in_experiment_workspace", "variant_id": variant_id}

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
        updated = await client.patch(
            _url("experiments"),
            params=_scoped_params({"id": f"eq.{experiment_id}"}),
            headers=_headers(prefer="return=representation"),
            json=patch,
        )
    return {"ok": updated.is_success, "experiment_id": experiment_id, "decision": decision}
