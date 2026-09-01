"""Automatic paid-media ingestion and experiment evaluation.

Provider APIs are read through adapters, normalized into performance_events, and
joined to Shopify attribution before the deterministic experiment engine runs.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .money_loop import evaluate, ingest_performance_event
from .providers import get_ads_provider
from .providers.base import ProviderMetrics


def _workspace_id() -> str:
    return os.getenv("BUFFER_BLASTER_WORKSPACE_ID", "").strip()


def _headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept-Profile": "buffer_blaster",
        "Content-Profile": "buffer_blaster",
    }


def _url(table: str) -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{table}"


def _configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and _workspace_id())


def _scoped_params(params: dict[str, str] | None = None) -> dict[str, str]:
    """PostgREST params for service-role reads, which bypass RLS."""
    scoped = {"workspace_id": f"eq.{_workspace_id()}"}
    if params:
        scoped.update(params)
    return scoped


async def _rows(table: str, params: dict[str, str]) -> list[dict[str, Any]]:
    if not _configured():
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url(table), params=_scoped_params(params), headers=_headers())
    data = response.json() if response.is_success else []
    return data if isinstance(data, list) else []


async def sync_experiment(experiment_id: str) -> dict[str, Any]:
    experiments = await _rows("experiments", {"id": f"eq.{experiment_id}", "limit": "1"})
    if not experiments:
        return {"ok": False, "error": "experiment_not_found_in_workspace"}
    experiment = experiments[0]
    variants = await _rows("experiment_variants", {"experiment_id": f"eq.{experiment_id}", "order": "created_at.asc"})
    if not variants:
        return {"ok": False, "error": "experiment_has_no_variants"}

    since = str(experiment.get("created_at") or "")[:10] or None
    until = datetime.now(timezone.utc).date().isoformat()
    sync_receipts: list[dict[str, Any]] = []

    for variant in variants:
        content_item_id = variant.get("content_item_id")
        refs = variant.get("external_ad_refs") or {}
        if not content_item_id or not isinstance(refs, dict):
            sync_receipts.append({"variant_id": variant["id"], "ok": False, "error": "content_item_or_external_refs_missing"})
            continue

        provider_refs: list[tuple[str, dict[str, Any]]] = []
        if refs.get("provider") in {"meta", "tiktok"}:
            provider_refs.append((str(refs["provider"]), refs))
        else:
            for provider_name in ("meta", "tiktok"):
                if isinstance(refs.get(provider_name), dict):
                    provider_refs.append((provider_name, refs[provider_name]))

        for provider_name, external_ref in provider_refs:
            try:
                provider = get_ads_provider(provider_name)
            except KeyError:
                sync_receipts.append({"variant_id": variant["id"], "provider": provider_name, "ok": False, "error": "unknown_provider"})
                continue
            result = await provider.get_metrics(external_ref, since=since, until=until)
            if not isinstance(result, ProviderMetrics):
                sync_receipts.append({"variant_id": variant["id"], "provider": provider_name, **result})
                continue
            written = 0
            for metric, value in result.metrics.items():
                receipt = await ingest_performance_event({
                    "content_item_id": content_item_id,
                    "source": provider_name,
                    "metric": metric,
                    "value": value,
                    "observed_at": result.observed_at,
                    "metadata": {"experiment_id": experiment_id, "variant_id": variant["id"], "external_ad_id": result.external_ad_id},
                })
                written += int(bool(receipt.get("ok")))
            sync_receipts.append({"variant_id": variant["id"], "provider": provider_name, "ok": True, "metrics_written": written})

    variant_results = await build_variant_results(experiment, variants)
    decision = await evaluate(experiment_id, variant_results) if variant_results else {"ok": False, "error": "no_evaluable_results"}
    return {"ok": True, "experiment_id": experiment_id, "sync": sync_receipts, "variant_results": variant_results, "decision": decision}


async def build_variant_results(experiment: dict[str, Any], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary_kpi = str(experiment.get("primary_kpi") or "roas").lower()
    out: list[dict[str, Any]] = []
    for variant in variants:
        content_item_id = variant.get("content_item_id")
        if not content_item_id:
            continue
        events = await _rows("performance_events", {"content_item_id": f"eq.{content_item_id}", "order": "observed_at.desc", "limit": "100"})
        latest: dict[str, float] = {}
        for event in events:
            metric = str(event.get("metric") or "")
            if metric and metric not in latest:
                latest[metric] = float(event.get("value") or 0)

        attribution = await _rows("attribution_events", {"variant_id": f"eq.{variant['id']}", "order": "occurred_at.asc", "limit": "1000"})
        revenue_cents = float(sum(int(row.get("revenue_cents") or 0) for row in attribution if row.get("event_type") == "orders.paid"))
        spend_cents = float(latest.get("spend_cents", 0))
        purchases = float(sum(1 for row in attribution if row.get("event_type") == "orders.paid"))

        if primary_kpi == "roas":
            value = revenue_cents / spend_cents if spend_cents else 0.0
        elif primary_kpi in {"revenue", "revenue_cents", "purchase_value_cents"}:
            value = revenue_cents
        elif primary_kpi in {"purchases", "conversions"}:
            value = purchases
        else:
            value = float(latest.get(primary_kpi, 0))

        sample_size = int(max(latest.get("impressions", 0), latest.get("clicks", 0), purchases))
        out.append({
            "variant_id": variant["id"],
            "role": variant["role"],
            "value": value,
            "spend_cents": int(spend_cents),
            "sample_size": sample_size,
        })
    return out
