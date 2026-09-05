"""Atomic server-owned usage wallets for paid trials and subscriptions.

Redis is the authorization source for provider spend because the production
stack already requires Redis and Lua lets us reserve both customer Ad Credits
and internal provider-cost budget atomically. Supabase remains the durable
reporting ledger; browser-provided balances are never trusted.
"""
from __future__ import annotations

import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import redis.asyncio as redis

from .pricing import package_for


_PREFIX = "buffer_blaster:wallet:v1:"
_SESSION_PREFIX = "buffer_blaster:stripe_session_wallet:v1:"
_RESERVATION_PREFIX = "buffer_blaster:wallet_reservation:v1:"

_RESERVE_LUA = r"""
local key = KEYS[1]
local reservation_key = KEYS[2]
local now_epoch = tonumber(ARGV[1])
local cost = tonumber(ARGV[2])
local credits_needed = tonumber(ARGV[3])
local reservation_ttl = tonumber(ARGV[4])

if redis.call('EXISTS', key) == 0 then
  return {'ERR', 'wallet_not_found'}
end

if reservation_key ~= '' and redis.call('EXISTS', reservation_key) == 1 then
  local previous_cost = tonumber(redis.call('HGET', reservation_key, 'estimated_provider_cost_cents') or '-1')
  local previous_credits = tonumber(redis.call('HGET', reservation_key, 'ad_credits_required') or '-1')
  if previous_cost ~= cost or previous_credits ~= credits_needed then
    return {'ERR', 'reservation_idempotency_conflict'}
  end
  return {
    'REPLAY',
    redis.call('HGET', reservation_key, 'remaining_provider_budget_after_cents') or '0',
    redis.call('HGET', reservation_key, 'remaining_ad_credits_after') or '0'
  }
end

local state = redis.call('HGET', key, 'state') or ''
if state ~= 'active' then
  return {'ERR', 'wallet_not_active'}
end
local expires_at = tonumber(redis.call('HGET', key, 'expires_at_epoch') or '0')
if expires_at > 0 and expires_at <= now_epoch then
  redis.call('HSET', key, 'state', 'expired')
  return {'ERR', 'wallet_expired'}
end
local budget = tonumber(redis.call('HGET', key, 'remaining_provider_budget_cents') or '0')
local credits = tonumber(redis.call('HGET', key, 'remaining_ad_credits') or '0')
if budget < cost then
  return {'ERR', 'provider_budget_exceeded', tostring(budget), tostring(credits)}
end
if credits < credits_needed then
  return {'ERR', 'ad_credits_exhausted', tostring(budget), tostring(credits)}
end
local new_budget = redis.call('HINCRBY', key, 'remaining_provider_budget_cents', -cost)
local new_credits = redis.call('HINCRBY', key, 'remaining_ad_credits', -credits_needed)
redis.call('HSET', key, 'updated_at_epoch', ARGV[1])

if reservation_key ~= '' then
  redis.call('HSET', reservation_key,
    'estimated_provider_cost_cents', tostring(cost),
    'ad_credits_required', tostring(credits_needed),
    'remaining_provider_budget_after_cents', tostring(new_budget),
    'remaining_ad_credits_after', tostring(new_credits),
    'created_at_epoch', ARGV[1]
  )
  redis.call('EXPIRE', reservation_key, reservation_ttl)
end
return {'OK', tostring(new_budget), tostring(new_credits)}
"""


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def _workspace_id() -> str:
    return (os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or "").strip()


def _client():
    url = _redis_url()
    if not url:
        return None
    return redis.from_url(url, decode_responses=True)


def _ttl_seconds(offer_id: str) -> int:
    if offer_id == "trial-7":
        return 7 * 24 * 3600
    if offer_id == "trial-30":
        return 30 * 24 * 3600
    return 31 * 24 * 3600


def _credits_required(estimated_provider_cost_cents: int) -> int:
    ceiling = max(1, int(os.getenv("STANDARD_AD_CREDIT_COST_CENTS", "100")))
    return max(1, math.ceil(max(0, estimated_provider_cost_cents) / ceiling))


def _reservation_key(wallet_id: str, idempotency_key: str | None) -> str:
    if not idempotency_key:
        return ""
    return f"{_RESERVATION_PREFIX}{wallet_id}:{idempotency_key}"


async def _mirror_wallet(wallet: dict[str, Any]) -> None:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    workspace_id = _workspace_id()
    if not (base and key and workspace_id):
        return
    payload = {
        "id": wallet["id"],
        "workspace_id": workspace_id,
        "customer_ref": wallet.get("customer_ref"),
        "offer_id": wallet["offer_id"],
        "remaining_ad_credits": wallet["remaining_ad_credits"],
        "remaining_provider_budget_cents": wallet["remaining_provider_budget_cents"],
        "expires_at": wallet.get("expires_at"),
        "state": wallet["state"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": "buffer_blaster",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            await http.post(f"{base}/rest/v1/usage_wallets?on_conflict=id", headers=headers, json=payload)
    except httpx.HTTPError:
        return


async def create_wallet(*, offer_id: str, customer_ref: str | None, checkout_session_id: str) -> dict[str, Any]:
    package = package_for(offer_id)
    if package is None:
        return {"ok": False, "error": "unknown_offer"}
    if not package.sellable:
        return {"ok": False, "error": "unsafe_offer_configuration", "offer": package.to_dict()}
    client = _client()
    if client is None:
        return {"ok": False, "error": "wallet_store_unavailable"}

    session_key = f"{_SESSION_PREFIX}{checkout_session_id}"
    try:
        existing = await client.get(session_key)
        if existing:
            wallet = await get_wallet(existing, client=client)
            return {"ok": True, "wallet": wallet, "idempotent": True}

        wallet_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=_ttl_seconds(offer_id))
        mapping = {
            "id": wallet_id,
            "workspace_id": _workspace_id(),
            "offer_id": offer_id,
            "customer_ref": customer_ref or "",
            "checkout_session_id": checkout_session_id,
            "remaining_ad_credits": package.included_ad_credits,
            "remaining_provider_budget_cents": package.provider_budget_cents,
            "state": "active",
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "expires_at_epoch": int(expires.timestamp()),
            "updated_at_epoch": int(now.timestamp()),
        }
        pipe = client.pipeline(transaction=True)
        pipe.hset(f"{_PREFIX}{wallet_id}", mapping=mapping)
        pipe.expire(f"{_PREFIX}{wallet_id}", _ttl_seconds(offer_id) + 7 * 24 * 3600)
        pipe.set(session_key, wallet_id, ex=_ttl_seconds(offer_id) + 30 * 24 * 3600, nx=True)
        results = await pipe.execute()
        if results[-1] is None:
            winner = await client.get(session_key)
            if winner:
                wallet = await get_wallet(winner, client=client)
                return {"ok": True, "wallet": wallet, "idempotent": True}
        wallet = _decode(mapping)
        await _mirror_wallet(wallet)
        return {"ok": True, "wallet": wallet, "idempotent": False}
    except redis.RedisError as exc:
        return {"ok": False, "error": "wallet_store_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()


def _decode(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}
    return {
        "id": str(raw.get("id") or ""),
        "workspace_id": str(raw.get("workspace_id") or "") or None,
        "offer_id": str(raw.get("offer_id") or ""),
        "customer_ref": str(raw.get("customer_ref") or "") or None,
        "checkout_session_id": str(raw.get("checkout_session_id") or "") or None,
        "remaining_ad_credits": int(raw.get("remaining_ad_credits") or 0),
        "remaining_provider_budget_cents": int(raw.get("remaining_provider_budget_cents") or 0),
        "state": str(raw.get("state") or "unknown"),
        "created_at": str(raw.get("created_at") or ""),
        "expires_at": str(raw.get("expires_at") or "") or None,
    }


async def get_wallet(wallet_id: str, *, client=None) -> dict[str, Any] | None:
    owns_client = client is None
    client = client or _client()
    if client is None:
        return None
    try:
        raw = await client.hgetall(f"{_PREFIX}{wallet_id}")
        if not raw:
            return None
        stored_workspace = str(raw.get("workspace_id") or "")
        current_workspace = _workspace_id()
        if current_workspace and stored_workspace and stored_workspace != current_workspace:
            return None
        wallet = _decode(raw)
        expires_epoch = int(raw.get("expires_at_epoch") or 0)
        if wallet["state"] == "active" and expires_epoch and expires_epoch <= int(time.time()):
            await client.hset(f"{_PREFIX}{wallet_id}", "state", "expired")
            wallet["state"] = "expired"
        return wallet
    except redis.RedisError:
        return None
    finally:
        if owns_client:
            await client.aclose()


async def reserve_generation(
    wallet_id: str,
    *,
    estimated_provider_cost_cents: int,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if estimated_provider_cost_cents < 0:
        return {"ok": False, "error": "invalid_provider_cost"}
    client = _client()
    if client is None:
        return {"ok": False, "error": "wallet_store_unavailable"}
    wallet = await get_wallet(wallet_id, client=client)
    if not wallet:
        await client.aclose()
        return {"ok": False, "error": "wallet_not_found"}
    credits_needed = _credits_required(estimated_provider_cost_cents)
    reservation_key = _reservation_key(wallet_id, idempotency_key)
    try:
        result = await client.eval(
            _RESERVE_LUA,
            2,
            f"{_PREFIX}{wallet_id}",
            reservation_key,
            int(time.time()),
            int(estimated_provider_cost_cents),
            int(credits_needed),
            7 * 24 * 3600,
        )
        if not result or result[0] not in {"OK", "REPLAY"}:
            error = result[1] if result and len(result) > 1 else "wallet_reservation_failed"
            return {
                "ok": False,
                "error": error,
                "remaining_provider_budget_cents": int(result[2]) if result and len(result) > 2 else None,
                "remaining_ad_credits": int(result[3]) if result and len(result) > 3 else None,
                "ad_credits_required": credits_needed,
            }
        replay = result[0] == "REPLAY"
        wallet = await get_wallet(wallet_id, client=client)
        if wallet and not replay:
            await _mirror_wallet(wallet)
        return {
            "ok": True,
            "wallet_id": wallet_id,
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "ad_credits_required": credits_needed,
            "remaining_provider_budget_after_cents": int(result[1]),
            "remaining_ad_credits_after": int(result[2]),
            "reservation_is_conservative": True,
            "idempotent_replay": replay,
            "idempotency_key": idempotency_key,
        }
    except redis.RedisError as exc:
        return {"ok": False, "error": "wallet_reservation_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()
