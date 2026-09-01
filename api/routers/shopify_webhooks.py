"""Shopify revenue webhooks for experiment attribution.

Webhook bodies are verified against the raw request bytes before parsing. Duplicate
Shopify deliveries are harmless because attribution_events enforces a unique
(source, external_event_id) key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Header, HTTPException, Request

from ..services.money_loop import ingest_attribution_event

router = APIRouter(prefix="/api/webhooks/shopify", tags=["shopify-webhooks"])

_ALLOWED_TOPICS = {"orders/create", "orders/paid", "orders/cancelled", "refunds/create"}


def verify_shopify_hmac(raw_body: bytes, supplied_hmac: str, secret: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, supplied_hmac or "")


def _attribution_ids(order: dict[str, Any]) -> tuple[str | None, str | None]:
    experiment_id: str | None = None
    variant_id: str | None = None

    for key in ("landing_site", "landing_site_ref", "referring_site"):
        raw = order.get(key)
        if not isinstance(raw, str) or not raw:
            continue
        query = parse_qs(urlparse(raw).query)
        experiment_id = experiment_id or (query.get("bb_exp") or [None])[0]
        variant_id = variant_id or (query.get("bb_var") or [None])[0]

    attributes = order.get("note_attributes") or order.get("custom_attributes") or []
    if isinstance(attributes, list):
        pairs = {str(item.get("name")): item.get("value") for item in attributes if isinstance(item, dict)}
        experiment_id = experiment_id or pairs.get("bb_exp")
        variant_id = variant_id or pairs.get("bb_var")

    return experiment_id, variant_id


def _event_id(event_id: str, webhook_id: str, payload: dict[str, Any]) -> str:
    return event_id or webhook_id or str(payload.get("id") or "")


def _money_cents(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(0, round(float(value) * 100))
    except (TypeError, ValueError):
        return None


@router.post("/orders")
async def order_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(default=""),
    x_shopify_topic: str = Header(default=""),
    x_shopify_webhook_id: str = Header(default=""),
    x_shopify_event_id: str = Header(default=""),
    x_shopify_shop_domain: str = Header(default=""),
) -> dict[str, Any]:
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="shopify_webhook_secret_not_configured")

    raw = await request.body()
    if not verify_shopify_hmac(raw, x_shopify_hmac_sha256, secret):
        raise HTTPException(status_code=401, detail="invalid_shopify_hmac")
    if x_shopify_topic not in _ALLOWED_TOPICS:
        raise HTTPException(status_code=400, detail="unsupported_shopify_topic")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_shopify_payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid_shopify_payload")

    experiment_id, variant_id = _attribution_ids(payload)
    event_id = _event_id(x_shopify_event_id, x_shopify_webhook_id, payload)
    if not event_id:
        # Do not create an un-deduplicatable row: an empty external_event_id would
        # collapse unrelated deliveries under the same unique key.
        raise HTTPException(status_code=400, detail="missing_shopify_event_id")
    order_ref = str(payload.get("admin_graphql_api_id") or payload.get("id") or "") or None
    total = payload.get("current_total_price") or payload.get("total_price")
    revenue_cents = 0 if x_shopify_topic in {"orders/cancelled", "refunds/create"} else _money_cents(total)

    result = await ingest_attribution_event({
        "source": "shopify",
        "event_type": x_shopify_topic.replace("/", "."),
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "external_event_id": event_id,
        "revenue_cents": revenue_cents,
        "order_ref": order_ref,
        "metadata": {
            "shop_domain": x_shopify_shop_domain,
            "currency": payload.get("currency") or payload.get("presentment_currency"),
            "financial_status": payload.get("financial_status"),
            "attributed": bool(experiment_id and variant_id),
        },
    })
    if not result.get("ok") and result.get("status") not in {200, 201, 409}:
        raise HTTPException(status_code=502, detail="attribution_persist_failed")
    return {"ok": True, "topic": x_shopify_topic, "event_id": event_id, "experiment_id": experiment_id, "variant_id": variant_id, "attributed": bool(experiment_id and variant_id)}
