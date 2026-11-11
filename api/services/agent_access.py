"""Agent identity, scoped tokens, and human-issued approvals.

Why this exists: the factory and publisher accept ``approved: true`` from the
caller. With a shared operator key, an agent could approve its own spend. This
module splits identities into *human* (operator API key or console session) and
*agent* (scoped ``bba_`` tokens). Agents can plan freely, but any spend or
publish needs an approval record that only a human identity can grant. Each
approval is bound to a payload hash, a cost ceiling, and is consumed once.

Redis is the runtime source of truth (same store as the wallet). Supabase
tables from migration 016 are a best-effort audit mirror.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis

from . import usage_wallet as _wallet
from .supabase_auth import EXECUTE_ROLES


def _client():
    # Resolved at call time so the shared wallet Redis client (and test doubles) apply.
    return _wallet._client()


def _workspace_id() -> str:
    return _wallet._workspace_id()

TOKEN_PREFIX = "bba_"
_TOKEN_KEY = "buffer_blaster:agent_token:v1:"
_TOKEN_INDEX = "buffer_blaster:agent_token_index:v1"
_APPROVAL_KEY = "buffer_blaster:approval:v1:"
_APPROVAL_INDEX = "buffer_blaster:approval_index:v1"

# read: inspect jobs/wallets/plans. plan: no-spend planning tools.
# render: may *request* and *use* render approvals. publish: same for publishing.
SCOPES = ("read", "plan", "render", "publish")
APPROVAL_KINDS = ("render", "publish")
APPROVAL_TTL_SECONDS = 24 * 3600

_CONSUME_LUA = r"""
-- op:consume_approval
local key = KEYS[1]
local payload_hash = ARGV[1]
local now_epoch = tonumber(ARGV[2])
local consumer = ARGV[3]
if redis.call('EXISTS', key) == 0 then
  return {'ERR', 'approval_not_found'}
end
local status = redis.call('HGET', key, 'status') or ''
if status == 'consumed' then
  return {'ERR', 'approval_already_used'}
end
if status ~= 'approved' then
  return {'ERR', 'approval_not_granted'}
end
local expires = tonumber(redis.call('HGET', key, 'expires_at_epoch') or '0')
if expires > 0 and expires <= now_epoch then
  return {'ERR', 'approval_expired'}
end
if redis.call('HGET', key, 'payload_sha256') ~= payload_hash then
  return {'ERR', 'approval_payload_mismatch'}
end
redis.call('HSET', key, 'status', 'consumed', 'consumed_at_epoch', tostring(now_epoch), 'consumed_by', consumer)
return {'OK', redis.call('HGET', key, 'max_cost_cents') or '0'}
"""


def _now() -> int:
    return int(time.time())


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def payload_hash(kind: str, payload: dict[str, Any]) -> str:
    """Canonical hash of what was approved. Control fields never count."""
    ignored = {"approved", "approval_id", "idempotency_key"}
    clean = {k: v for k, v in sorted(payload.items()) if k not in ignored and v is not None}
    return _sha(json.dumps({"kind": kind, "payload": clean}, sort_keys=True, separators=(",", ":"), default=str))


def is_agent(identity: str | None) -> bool:
    return bool(identity) and str(identity).startswith("agent:")


async def _mirror(table: str, row: dict[str, Any]) -> None:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    workspace_id = _workspace_id()
    if not (base and key and workspace_id):
        return
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": "buffer_blaster",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            await http.post(f"{base}/rest/v1/{table}?on_conflict=id", headers=headers, json={**row, "workspace_id": workspace_id})
    except httpx.HTTPError:
        return


def _iso(epoch: int | None) -> str | None:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat() if epoch else None


# ---------------------------------------------------------------- tokens

async def create_agent_token(*, name: str, scopes: list[str], ttl_days: int, created_by: str) -> dict[str, Any]:
    name = " ".join((name or "").split())[:80]
    if len(name) < 2:
        return {"ok": False, "error": "invalid_name"}
    wanted = sorted(set(scopes or []))
    if not wanted or any(s not in SCOPES for s in wanted):
        return {"ok": False, "error": "invalid_scopes", "allowed": list(SCOPES)}
    if not 1 <= int(ttl_days) <= 365:
        return {"ok": False, "error": "invalid_ttl_days"}
    client = _client()
    if client is None:
        return {"ok": False, "error": "token_store_unavailable"}
    token_id = uuid.uuid4().hex[:16]
    secret = secrets.token_urlsafe(32)
    now = _now()
    expires = now + int(ttl_days) * 86400
    record = {
        "id": token_id, "name": name, "scopes": ",".join(wanted), "secret_sha256": _sha(secret),
        "created_at_epoch": str(now), "expires_at_epoch": str(expires), "revoked": "0",
        "created_by": created_by, "workspace_id": _workspace_id(), "last_used_at_epoch": "0",
    }
    try:
        await client.hset(f"{_TOKEN_KEY}{token_id}", mapping=record)
        await client.hset(_TOKEN_INDEX, token_id, name)
    except redis.RedisError as exc:
        return {"ok": False, "error": "token_store_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()
    await _mirror("agent_tokens", {"id": token_id, "name": name, "scopes": wanted, "created_by": created_by,
                                   "expires_at": _iso(expires), "revoked_at": None})
    # The plaintext token is returned exactly once and never stored.
    return {"ok": True, "token": f"{TOKEN_PREFIX}{token_id}_{secret}", "token_id": token_id, "name": name,
            "scopes": wanted, "expires_at": _iso(expires), "shown_once": True}


def _public_token(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_id": raw.get("id"), "name": raw.get("name"), "scopes": [s for s in str(raw.get("scopes", "")).split(",") if s],
        "created_at": _iso(int(raw.get("created_at_epoch") or 0)), "expires_at": _iso(int(raw.get("expires_at_epoch") or 0)),
        "revoked": raw.get("revoked") == "1", "created_by": raw.get("created_by"),
        "last_used_at": _iso(int(raw.get("last_used_at_epoch") or 0)),
    }


async def list_agent_tokens() -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "token_store_unavailable"}
    try:
        index = await client.hgetall(_TOKEN_INDEX)
        rows = []
        for token_id in sorted(index):
            raw = await client.hgetall(f"{_TOKEN_KEY}{token_id}")
            if raw and raw.get("workspace_id", "") == _workspace_id():
                rows.append(_public_token(raw))
        return {"ok": True, "tokens": rows}
    finally:
        await client.aclose()


async def revoke_agent_token(token_id: str, *, revoked_by: str) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "token_store_unavailable"}
    try:
        key = f"{_TOKEN_KEY}{token_id}"
        raw = await client.hgetall(key)
        if not raw or raw.get("workspace_id", "") != _workspace_id():
            return {"ok": False, "error": "token_not_found"}
        await client.hset(key, mapping={"revoked": "1", "revoked_at_epoch": str(_now()), "revoked_by": revoked_by})
    finally:
        await client.aclose()
    await _mirror("agent_tokens", {"id": token_id, "name": raw.get("name"), "scopes": raw.get("scopes", "").split(","),
                                   "created_by": raw.get("created_by"), "revoked_at": _iso(_now())})
    return {"ok": True, "token_id": token_id, "revoked": True}


async def verify_agent_token(token: str) -> dict[str, Any] | None:
    """Return the agent record for a valid, unrevoked, unexpired token, else None."""
    if not token.startswith(TOKEN_PREFIX):
        return None
    body = token[len(TOKEN_PREFIX):]
    token_id, _, secret = body.partition("_")
    if not token_id or not secret:
        return None
    client = _client()
    if client is None:
        return None
    try:
        raw = await client.hgetall(f"{_TOKEN_KEY}{token_id}")
        if not raw:
            return None
        if not hmac.compare_digest(str(raw.get("secret_sha256", "")), _sha(secret)):
            return None
        if raw.get("revoked") == "1" or int(raw.get("expires_at_epoch") or 0) <= _now():
            return None
        if raw.get("workspace_id", "") != _workspace_id():
            return None
        await client.hset(f"{_TOKEN_KEY}{token_id}", "last_used_at_epoch", str(_now()))
        return {"id": token_id, "name": raw.get("name"), "scopes": [s for s in raw.get("scopes", "").split(",") if s]}
    except redis.RedisError:
        return None
    finally:
        await client.aclose()


# ------------------------------------------------------------- approvals

async def request_approval(*, kind: str, payload: dict[str, Any], requested_by: str, max_cost_cents: int = 0,
                           summary: str = "") -> dict[str, Any]:
    if kind not in APPROVAL_KINDS:
        return {"ok": False, "error": "invalid_approval_kind", "allowed": list(APPROVAL_KINDS)}
    client = _client()
    if client is None:
        return {"ok": False, "error": "approval_store_unavailable"}
    approval_id = str(uuid.uuid4())
    now = _now()
    record = {
        "id": approval_id, "kind": kind, "status": "pending", "payload_sha256": payload_hash(kind, payload),
        "payload_json": json.dumps(payload, sort_keys=True, default=str)[:20000], "max_cost_cents": str(max(0, int(max_cost_cents))),
        "summary": (summary or "")[:500], "requested_by": requested_by, "requested_at_epoch": str(now),
        "expires_at_epoch": str(now + APPROVAL_TTL_SECONDS), "workspace_id": _workspace_id(),
    }
    try:
        await client.hset(f"{_APPROVAL_KEY}{approval_id}", mapping=record)
        await client.hset(_APPROVAL_INDEX, approval_id, kind)
    finally:
        await client.aclose()
    await _mirror("agent_approvals", {"id": approval_id, "kind": kind, "status": "pending", "payload_sha256": record["payload_sha256"],
                                      "max_cost_cents": int(record["max_cost_cents"]), "requested_by": requested_by, "summary": record["summary"]})
    return {"ok": True, "approval_id": approval_id, "status": "pending", "kind": kind, "max_cost_cents": int(record["max_cost_cents"]),
            "expires_at": _iso(now + APPROVAL_TTL_SECONDS), "next": "A human operator must approve this in the console or via POST /api/agent/approvals/{id}/decision."}


def _public_approval(raw: dict[str, Any]) -> dict[str, Any]:
    payload: Any
    try:
        payload = json.loads(raw.get("payload_json") or "{}")
    except ValueError:
        payload = {}
    return {
        "approval_id": raw.get("id"), "kind": raw.get("kind"), "status": raw.get("status"), "summary": raw.get("summary"),
        "max_cost_cents": int(raw.get("max_cost_cents") or 0), "payload": payload, "requested_by": raw.get("requested_by"),
        "decided_by": raw.get("decided_by"), "requested_at": _iso(int(raw.get("requested_at_epoch") or 0)),
        "expires_at": _iso(int(raw.get("expires_at_epoch") or 0)), "consumed_by": raw.get("consumed_by"),
    }


async def get_approval(approval_id: str) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "approval_store_unavailable"}
    try:
        raw = await client.hgetall(f"{_APPROVAL_KEY}{approval_id}")
    finally:
        await client.aclose()
    if not raw or raw.get("workspace_id", "") != _workspace_id():
        return {"ok": False, "error": "approval_not_found"}
    return {"ok": True, "approval": _public_approval(raw)}


async def list_approvals(status: str | None = None) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "approval_store_unavailable"}
    try:
        index = await client.hgetall(_APPROVAL_INDEX)
        rows = []
        for approval_id in index:
            raw = await client.hgetall(f"{_APPROVAL_KEY}{approval_id}")
            if raw and raw.get("workspace_id", "") == _workspace_id() and (not status or raw.get("status") == status):
                rows.append(_public_approval(raw))
        rows.sort(key=lambda r: r.get("requested_at") or "", reverse=True)
        return {"ok": True, "approvals": rows}
    finally:
        await client.aclose()


async def decide_approval(approval_id: str, *, decision: str, decided_by: str) -> dict[str, Any]:
    """Human-only. Callers must reject agent identities before calling this."""
    if is_agent(decided_by):
        return {"ok": False, "error": "human_identity_required"}
    if decision not in {"approved", "rejected"}:
        return {"ok": False, "error": "invalid_decision"}
    client = _client()
    if client is None:
        return {"ok": False, "error": "approval_store_unavailable"}
    key = f"{_APPROVAL_KEY}{approval_id}"
    try:
        raw = await client.hgetall(key)
        if not raw or raw.get("workspace_id", "") != _workspace_id():
            return {"ok": False, "error": "approval_not_found"}
        if raw.get("status") != "pending":
            return {"ok": False, "error": "approval_not_pending", "status": raw.get("status")}
        if int(raw.get("expires_at_epoch") or 0) <= _now():
            return {"ok": False, "error": "approval_expired"}
        await client.hset(key, mapping={"status": decision, "decided_by": decided_by, "decided_at_epoch": str(_now())})
    finally:
        await client.aclose()
    await _mirror("agent_approvals", {"id": approval_id, "kind": raw.get("kind"), "status": decision, "payload_sha256": raw.get("payload_sha256"),
                                      "max_cost_cents": int(raw.get("max_cost_cents") or 0), "requested_by": raw.get("requested_by"),
                                      "decided_by": decided_by, "summary": raw.get("summary")})
    return {"ok": True, "approval_id": approval_id, "status": decision}


async def consume_approval(approval_id: str, *, kind: str, payload: dict[str, Any], consumer: str) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "approval_store_unavailable"}
    try:
        raw_kind = await client.hget(f"{_APPROVAL_KEY}{approval_id}", "kind")
        if raw_kind is not None and raw_kind != kind:
            return {"ok": False, "error": "approval_kind_mismatch"}
        result = await client.eval(_CONSUME_LUA, 1, f"{_APPROVAL_KEY}{approval_id}", payload_hash(kind, payload), _now(), consumer)
        if not result or result[0] != "OK":
            return {"ok": False, "error": result[1] if result and len(result) > 1 else "approval_consume_failed"}
        return {"ok": True, "approval_id": approval_id, "max_cost_cents": int(result[1])}
    except redis.RedisError as exc:
        return {"ok": False, "error": "approval_consume_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()


async def restore_approval(approval_id: str) -> None:
    """Undo a consume when spend was blocked before any reservation happened."""
    client = _client()
    if client is None:
        return
    try:
        key = f"{_APPROVAL_KEY}{approval_id}"
        if await client.hget(key, "status") == "consumed":
            await client.hset(key, mapping={"status": "approved", "consumed_by": "", "consumed_at_epoch": "0"})
    except redis.RedisError:
        return
    finally:
        await client.aclose()


PUBLISH_FIELDS = ("content", "platforms", "scheduled_at", "media_urls", "campaign_id", "format")


def publish_payload(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: fields.get(k) for k in PUBLISH_FIELDS if fields.get(k) is not None}


async def gate_publish(*, identity: str, fields: dict[str, Any], approved: bool, approval_id: str | None,
                       role: str | None = None) -> dict[str, Any]:
    """Humans pass with approved=True. Agents need a consumed human approval."""
    if not is_agent(identity):
        if approved and role is not None and role not in EXECUTE_ROLES:
            return {"ok": False, "error": "role_denied", "detail": f"Role '{role}' cannot publish."}
        return {"ok": bool(approved)} if approved else {"ok": False, "error": "human_approval_required"}
    if not approval_id:
        return {"ok": False, "error": "human_approval_required", "approval_required": True,
                "next": "Call request_publish_approval, wait for a human decision, then pass approval_id."}
    consumed = await consume_approval(approval_id, kind="publish", payload=publish_payload(fields), consumer=identity)
    return consumed if not consumed.get("ok") else {"ok": True, "approval_id": approval_id}
