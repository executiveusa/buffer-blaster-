"""Stripe checkout verification and idempotent usage-wallet activation."""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

from .pricing import package_for
from .usage_wallet import create_wallet


async def fetch_checkout_session(session_id: str) -> dict[str, Any]:
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return {"ok": False, "error": "stripe_not_configured"}
    if not session_id.startswith("cs_"):
        return {"ok": False, "error": "invalid_checkout_session_id"}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(
                f"https://api.stripe.com/v1/checkout/sessions/{quote(session_id, safe='')}",
                headers={"Authorization": f"Bearer {secret}"},
            )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": "stripe_unreachable", "detail": type(exc).__name__}
    if response.is_error:
        return {"ok": False, "error": "stripe_session_fetch_failed", "status": response.status_code, "detail": response.text[:500]}
    return {"ok": True, "session": response.json()}


async def activate_checkout_session(session_id: str) -> dict[str, Any]:
    fetched = await fetch_checkout_session(session_id)
    if not fetched.get("ok"):
        return fetched
    session = fetched.get("session") or {}
    offer_id = str((session.get("metadata") or {}).get("offer") or "")
    package = package_for(offer_id)
    if package is None or not package.sellable:
        return {"ok": False, "error": "invalid_checkout_offer", "offer_id": offer_id or None}
    if str(session.get("payment_status") or "") != "paid":
        return {"ok": False, "error": "checkout_not_paid", "payment_status": session.get("payment_status")}
    if str(session.get("currency") or "").lower() != "usd":
        return {"ok": False, "error": "checkout_currency_mismatch", "currency": session.get("currency")}
    amount_total = int(session.get("amount_total") or 0)
    if amount_total != package.price_cents:
        return {
            "ok": False,
            "error": "checkout_amount_mismatch",
            "expected_cents": package.price_cents,
            "received_cents": amount_total,
        }
    customer = session.get("customer") or session.get("customer_details", {}).get("email")
    return await create_wallet(
        offer_id=offer_id,
        customer_ref=str(customer) if customer else None,
        checkout_session_id=str(session.get("id") or session_id),
    )
