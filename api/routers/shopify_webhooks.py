"""Shopify revenue webhooks for experiment attribution.

Webhook bodies are verified against the raw request bytes before parsing. Duplicate
Shopify deliveries are harmless because attribution_events enforces a unique
(source, external_event_id) key.

Financial truth rule: orders/paid creates positive revenue. refunds/create and
orders/cancelled are lifecycle evidence only. A successful refund adjustment is
recorded from order_transactions/create with kind=refund, because Shopify notes
that refunds/create is independent from the movement of money.
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

from ..services.money_loop import find_order_attribution, ingest_attribution_event

router = APIRouter(prefix="/api/webhooks/shopify", tags=["shopify-webhooks"])

_ALLOWED_TOPICS = {
    "orders/create",
    "orders/paid",
    "orders/cancelled",
    "refunds/create",
    "order_transactions/create",
}


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


def _money_cents(value: Any, *, signed: bool = False) -> int | None:
    if value in (None, ""):
        return None
    try:
        cents = round(float(value) * 100)
        return cents if signed else max(0, cents)
    except (TypeError, ValueError):
        return None


def _order_ref(topic: str, payload: dict[str, Any]) -> str | None:
    """Use Shopify's numeric order id consistently across order/refund/transaction topics."""
    value = payload.get("order_id") if topic in {"refunds/create", "order_transactions/create"} else payload.get("id")
    return str(value) if value not in (None, "") else None


def _financial_adjustment(topic: str, payload: dict[str, Any]) -> tuple[int | None, str]:
    if topic == "orders/paid":
        total = payload.get("current_total_price") or payload.get("total_price")
        return _money_cents(total), "gross_payment"
    if topic == "order_transactions/create":
        kind = str(payload.get("kind") or "").lower()
        status = str(payload.get("status") or "").lower()
        if kind == "refund" and status == "success":
            amount = _money_cents(payload.get("amount"), signed=True)
            return (-abs(amount) if amount is not None else None), "successful_refund"
        return 0, "non_refund_or_unsuccessful_transaction"
    return 0, "lifecycle_only"


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

    event_id = _event_id(x_shopify_event_id, x_shopify_webhook_id, payload)
    if not event_id:
        raise HTTPException(status_code=400, detail="missing_shopify_event_id")

    order_ref = _order_ref(x_shopify_topic, payload)
    experiment_id, variant_id = _attribution_ids(payload)
    inherited = False
    if order_ref and not (experiment_id and variant_id):
        original = await find_order_attribution(order_ref)
        if original:
            experiment_id = str(original.get("experiment_id") or "") or None
            variant_id = str(original.get("variant_id") or "") or None
            inherited = bool(experiment_id and variant_id)

    revenue_cents, financial_semantic = _financial_adjustment(x_shopify_topic, payload)
    if x_shopify_topic == "order_transactions/create":
        kind = str(payload.get("kind") or "").lower()
        status = str(payload.get("status") or "").lower()
        if kind == "refund" and status == "success" and revenue_cents is None:
            raise HTTPException(status_code=400, detail="missing_refund_transaction_amount")

    currency = payload.get("currency") or payload.get("presentment_currency")
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
            "currency": currency,
            "financial_status": payload.get("financial_status") or payload.get("status"),
            "transaction_kind": payload.get("kind"),
            "financial_semantic": financial_semantic,
            "attributed": bool(experiment_id and variant_id),
            "attribution_inherited_from_paid_order": inherited,
        },
    })
    if not result.get("ok") and result.get("status") not in {200, 201, 409}:
        raise HTTPException(status_code=502, detail="attribution_persist_failed")
    return {
        "ok": True,
        "topic": x_shopify_topic,
        "event_id": event_id,
        "order_ref": order_ref,
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "revenue_cents": revenue_cents,
        "financial_semantic": financial_semantic,
        "attributed": bool(experiment_id and variant_id),
    }
