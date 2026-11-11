"""S4 spend ledger: one append-only ledger, actuals only from provider responses.

Runtime truth lives in Redis (list + running totals per workspace, matching the
repo's Redis-primary + PostgREST-mirror pattern from 016/018); migration 019's
buffer_blaster.usage_events is the durable queryable copy.

Money-boundary rules (reviewer findings, S4 r2):
- actual_cents is recorded only when the caller got it from a provider
  response; estimated and actual are separate fields and are never summed
  together. An event with NEITHER is rejected (cost_unknown) - unknown cost
  never silently counts as zero.
- Caps are validated at write time (non-negative integers only). An invalid
  stored cap fails CLOSED: paid execution blocks with cap_config_invalid,
  it never silently disables the cap.
- Cap enforcement is atomic across concurrent runs: check_and_hold moves the
  estimated amount into per-window held counters with atomic HINCRBY +
  rollback-on-violation, so two runs cannot jointly exceed a cap. The hold is
  the accounting; record_usage settles held -> spent.
- PostgREST mirror failures are detected (status checked), logged and tracked
  in a durable backlog; while the mirror is behind, check_and_hold fails
  closed (ledger_mirror_backlog) until reconcile_mirror() provably replays the
  backlog and rebuilds totals from the durable mirror. If Redis is reset, the
  first hold rebuilds totals from the mirror before admitting spend. Hosts
  must still run Redis with AOF (appendonly yes) - documented in
  docs/USAGE_AND_CAPS.md; we do not guess host persistence.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

import httpx
import redis.asyncio as redis

from . import runtime_settings

log = logging.getLogger("buffer_blaster.usage_ledger")

_CAP_KEYS = ("USAGE_CAP_JOB_CENTS", "USAGE_CAP_DAILY_CENTS", "USAGE_CAP_MONTHLY_CENTS")
_KINDS = {"llm", "vision", "image", "video", "transcribe"}


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def _workspace_id() -> str:
    return os.getenv("STUDIO_WORKSPACE_ID", "").strip() or os.getenv("BUFFER_BLASTER_WORKSPACE_ID", "").strip()


def _list_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_events:{workspace_id}"


def _totals_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_totals:{workspace_id}"


def _backlog_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_mirror_backlog:{workspace_id}"


def _backlog_payload_key(workspace_id: str, event_id: str) -> str:
    return f"buffer_blaster:usage_mirror_backlog_payload:{workspace_id}:{event_id}"


def _reconciled_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_reconciled:{workspace_id}"


def _holds_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_holds:{workspace_id}"


def _rebuild_lock_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_rebuild_lock:{workspace_id}"


def _release_queue_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_pending_release:{workspace_id}"


def _pending_settle_key(workspace_id: str) -> str:
    return f"buffer_blaster:usage_pending_settle:{workspace_id}"


#: Rebuild lock TTL. The holder RENEWS it between mirror pages (fenced by its
#: token), so a slow multi-page rebuild never lapses mid-rewrite; a crashed
#: holder's lock expires and the next reconcile re-acquires and rebuilds.
_REBUILD_LOCK_MS = 15_000
#: How long settle waits for a rebuild before deferring to the rebuild's own
#: drain step (never settles concurrently with a rewrite).
_SETTLE_WAIT_S = 30.0

# Atomic mutation guard (r5): every totals mutation runs inside one Lua step
# that refuses to run while a rebuild holds the lock - no mutation can land
# between the rebuild's mirror read and its totals rewrite.
_LUA_GUARDED_HINCRBY = """
if redis.call('GET', KEYS[2]) then return 0 end
for i = 1, #ARGV, 2 do
  redis.call('HINCRBY', KEYS[1], ARGV[i], tonumber(ARGV[i+1]))
end
return 1
"""
_LUA_RENEW = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('PEXPIRE', KEYS[1], ARGV[2])
end
return 0
"""
#: Atomic token-checked totals rewrite: the ENTIRE rebuild commit (delete
#: totals, apply every increment, clear the drained pending list, set the
#: reconciled flag) executes only while our fencing token still owns the
#: lock. A renew-then-rewrite pair would be check-then-act: the lock can
#: expire between them and a second worker's rebuild could be clobbered.
#: ARGV: [1]=token, [2]=captured pending-settle count, [3]=captured
#: release-queue count, [4..n-1]=field,delta pairs, [n]=flag timestamp.
#: Both queues are LTRIM-med to exactly the captured prefix: an event or
#: release that lands between our read and this commit SURVIVES for the
#: next reconcile (a DEL would silently lose it = cap undercount).
_LUA_GUARDED_REWRITE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('DEL', KEYS[2])
for i = 4, #ARGV - 1, 2 do
  redis.call('HINCRBY', KEYS[2], ARGV[i], tonumber(ARGV[i + 1]))
end
redis.call('LTRIM', KEYS[3], tonumber(ARGV[2]), -1)
redis.call('LTRIM', KEYS[5], tonumber(ARGV[3]), -1)
redis.call('SET', KEYS[4], ARGV[#ARGV])
return 1
"""

_LUA_RELEASE_LOCK = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


def _mirror_env() -> tuple[str, str]:
    return (os.getenv("SUPABASE_URL", "").rstrip("/"),
            os.getenv("SUPABASE_SERVICE_KEY", ""))


def _windows(job_id: str | None, now: time.struct_time | None = None) -> dict[str, str]:
    now = now or time.gmtime()
    out = {"day": time.strftime("%Y-%m-%d", now), "month": time.strftime("%Y-%m", now)}
    if job_id:
        out["job"] = str(job_id)
    return out


def _field(window: str, value: str, held: bool = False) -> str:
    return f"{'held' if held else 'spent'}:{window}:{value}"


# ---------------------------------------------------------------- caps


def parse_cap(raw: str) -> int | None:
    """A cap is a non-negative integer of cents. None = invalid (fail closed)."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


async def read_caps() -> dict[str, Any]:
    """Read the three owner caps. Invalid stored values are reported, never
    coerced to 0 (which would silently disable the cap)."""
    caps: dict[str, int] = {}
    invalid: list[str] = []
    for key in _CAP_KEYS:
        raw = await runtime_settings.get_value(key, "0")
        if str(raw).strip() in ("", "0"):
            caps[key] = 0
            continue
        value = parse_cap(str(raw))
        if value is None:
            invalid.append(key)
        else:
            caps[key] = value
    if invalid:
        return {"ok": False, "error": "cap_config_invalid", "invalid_keys": invalid}
    return {"ok": True, "caps": caps}


async def check_and_hold(
    *,
    job_id: str | None,
    estimated_cents: int | None,
    workspace_id: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Atomic cap check + hold, admitted before any wallet reservation.

    Concurrency safety without Lua: each window counter is moved with one
    atomic HINCRBY and checked against its cap; any violation rolls the hold
    back. An interleaving run can only observe a state where a violator is
    about to roll back, so admitted holds never jointly exceed a cap (a
    transient overshoot can conservatively reject a run that would have fit -
    fail-closed, retry-safe).
    """
    if estimated_cents is None:
        return {"ok": False, "error": "estimate_required",
                "detail": "Unknown cost is rejected before execution; an estimate is mandatory."}
    est = int(estimated_cents)
    if est < 0:
        return {"ok": False, "error": "estimate_invalid"}

    caps = await read_caps()
    if not caps.get("ok"):
        return caps  # fail closed on invalid owner configuration
    cap_values = caps["caps"]
    ws = workspace_id or _workspace_id()
    url = _redis_url()
    mirror_configured = all(_mirror_env())
    if not any(cap_values.values()):
        if not mirror_configured:
            # No caps and Redis-only mode: nothing to enforce or hold.
            return {"ok": True, "caps_configured": False, "hold": None}
    if not url:
        return {"ok": False, "error": "cap_check_unavailable",
                "detail": "Caps are configured but the ledger store is unreachable; failing closed."}
    if not ws:
        return {"ok": False, "error": "workspace_not_configured"}

    owns = client is None
    client = client or redis.from_url(url, decode_responses=True)
    try:
        # A totals rebuild quiesces new holds: fail closed (retry-safe) while
        # reconcile rewrites the totals hash, so no hold lands mid-rebuild.
        if await client.get(_rebuild_lock_key(ws)):
            return {"ok": False, "error": "ledger_rebuild_in_progress",
                    "detail": "Cap totals are being rebuilt from the durable mirror; retry shortly."}
        release_queued = await client.llen(_release_queue_key(ws))
        if mirror_configured or release_queued:
            backlog = await client.scard(_backlog_key(ws)) if mirror_configured else 0
            flag = await client.get(_reconciled_key(ws))
            if backlog or not flag or release_queued:
                reconciled = await reconcile_mirror(workspace_id=ws, client=client)
                if not reconciled.get("ok") or reconciled.get("backlog_remaining"):
                    return {"ok": False, "error": "ledger_mirror_backlog",
                            "detail": "Durable usage mirror is behind; failing closed until reconcile_mirror succeeds.",
                            "reconcile": reconciled}
        windows = _windows(job_id)
        caps_by_window = {"job": cap_values["USAGE_CAP_JOB_CENTS"],
                          "day": cap_values["USAGE_CAP_DAILY_CENTS"],
                          "month": cap_values["USAGE_CAP_MONTHLY_CENTS"]}
        held_fields: list[tuple[str, str]] = []  # (window, field)
        try:
            for window, value in windows.items():
                held = _field(window, value, held=True)
                # guarded: the increment cannot land mid-rebuild
                done = await client.eval(_LUA_GUARDED_HINCRBY, 2,
                                         _totals_key(ws), _rebuild_lock_key(ws),
                                         held, str(est))
                if not done:
                    raise _RebuildBusy()
                held_fields.append((window, held))
                cap = caps_by_window[window]
                if cap:
                    held_now = int(await client.hget(_totals_key(ws), held) or 0)
                    spent_now = int(await client.hget(_totals_key(ws), _field(window, value)) or 0)
                    if spent_now + held_now > cap:
                        raise _CapExceeded(window=window, cap=cap, spent=spent_now, held=held_now)
        except _RebuildBusy:
            for _, held in held_fields:
                await client.hincrby(_totals_key(ws), held, -est)
            return {"ok": False, "error": "ledger_rebuild_in_progress",
                    "detail": "Cap totals are being rebuilt from the durable mirror; retry shortly."}
        except _CapExceeded as exceeded:
            for _, held in held_fields:
                await client.hincrby(_totals_key(ws), held, -est)
            if exceeded.window == "job":
                return {"ok": False, "error": "job_cap_exceeded", "job_id": job_id,
                        "job_cap_cents": exceeded.cap,
                        "job_committed_cents": exceeded.spent + exceeded.held - est,
                        "additional_estimated_cents": est}
            return {"ok": False, "error": "workspace_cap_exceeded", "window": exceeded.window,
                    "workspace_cap_cents": exceeded.cap,
                    "workspace_committed_cents": exceeded.spent + exceeded.held - est,
                    "additional_estimated_cents": est}
        # Register the hold by unique id so release is idempotent (M2): a
        # double-release finds no record and is a no-op. Reconcile rebuilds
        # held sums from this hash, which also self-heals a hold record lost
        # to a crash between the increments above and this write.
        hold_id = str(uuid.uuid4())
        await client.hset(_holds_key(ws), hold_id, json.dumps(
            {"est_cents": est, "windows": windows, "job_id": job_id,
             "created_at_epoch": int(time.time())}))
        return {"ok": True, "caps_configured": bool(any(cap_values.values())),
                "hold": {"workspace_id": ws, "hold_id": hold_id, "est_cents": est, "windows": windows}}
    except redis.RedisError as exc:
        return {"ok": False, "error": "cap_check_unavailable", "detail": type(exc).__name__}
    finally:
        if owns:
            await client.aclose()


class _RebuildBusy(Exception):
    pass


class _CapExceeded(Exception):
    def __init__(self, *, window: str, cap: int, spent: int, held: int):
        super().__init__(window)
        self.window, self.cap, self.spent, self.held = window, cap, spent, held


async def release_hold(hold: dict[str, Any] | None, *, client: Any | None = None) -> None:
    """Release the un-settled remainder of a hold (refund / partial recording).

    Idempotent by hold_id (M2): the release only executes while the hold's
    record exists, inside a WATCH/MULTI transaction, so a double-release -
    including two concurrent releases - decrements cap totals exactly once.
    """
    if not hold:
        return
    ws = hold["workspace_id"]
    est = int(hold.get("est_cents") or 0)
    if est <= 0:
        return
    url = _redis_url()
    if not url:
        return
    owns = client is None
    client = client or redis.from_url(url, decode_responses=True)
    holds_key = _holds_key(ws)
    hold_id = hold.get("hold_id")
    held_fields = [_field(window, value, held=True) for window, value in hold.get("windows", {}).items()]
    # One Lua script = one atomic step on the server: the decrement happens
    # only while the hold record exists, so any number of concurrent or
    # repeated releases decrement exactly once.
    # During a rebuild the release is QUEUED atomically (same Lua step as
    # the lock check): the rebuild drains the queue inside its commit, so a
    # deferred release is never lost and never applied twice (HDEL of the
    # hold record is idempotent). No caller retry is required for liveness:
    # the queue is durable and every reconcile drains it.
    script = """
    if redis.call('GET', KEYS[3]) then redis.call('RPUSH', KEYS[4], ARGV[1]) return 2 end
    if redis.call('HDEL', KEYS[1], ARGV[1]) == 0 then return 0 end
    for i = 3, #ARGV do redis.call('HINCRBY', KEYS[2], ARGV[i], -tonumber(ARGV[2])) end
    return 1
    """
    try:
        released = await client.eval(script, 4, holds_key, _totals_key(ws),
                                     _rebuild_lock_key(ws), _release_queue_key(ws),
                                     hold_id or "", str(est), *held_fields)
        if released == 2:
            # Rebuild in flight: the hold record stays, the rebuild preserves
            # it, and a later release retries. Conservative, never a cap leak.
            log.warning("usage hold release deferred during rebuild; hold_id=%s", hold_id)
    except redis.RedisError:
        log.warning("usage hold release failed", exc_info=True)
    finally:
        if owns:
            await client.aclose()


# ---------------------------------------------------------------- recording


async def record_usage(
    *,
    actor: str,
    provider: str,
    model: str,
    kind: str,
    job_id: str | None = None,
    approval_id: str | None = None,
    reasoning_level: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    estimated_cents: int | None = None,
    actual_cents: int | None = None,
    priced_actual_cents: int | None = None,
    cost_provenance: str | None = None,
    wallet_credits: int | None = None,
    workspace_id: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Append one provider-call row. actual_cents must come from a provider
    response, never a silent estimate; estimated vs actual are never mixed.
    priced_actual_cents is a SEPARATE, labeled field: token counts reported
    by the provider priced at the configured vendor list price
    (cost_provenance='computed_from_provider_tokens'). It never overwrites
    actual_cents, so the provider-actuals-only requirement is preserved.
    All-None cost is rejected: unknown cost never counts as zero."""
    ws = workspace_id or _workspace_id()
    if not ws:
        return {"ok": False, "error": "workspace_not_configured"}
    if kind not in _KINDS:
        return {"ok": False, "error": "invalid_kind", "allowed": sorted(_KINDS)}
    if not actor or not provider or not model:
        return {"ok": False, "error": "actor_provider_model_required"}
    if estimated_cents is None and actual_cents is None and priced_actual_cents is None:
        return {"ok": False, "error": "cost_unknown",
                "detail": "estimated_cents, priced_actual_cents or actual_cents is required; unknown cost is never recorded as zero."}
    if actual_cents is not None and priced_actual_cents is not None:
        return {"ok": False, "error": "cost_fields_mixed",
                "detail": "actual_cents (provider-reported) and priced_actual_cents (computed) are never recorded together."}
    if priced_actual_cents is not None and cost_provenance != "computed_from_provider_tokens":
        return {"ok": False, "error": "provenance_required",
                "detail": "priced_actual_cents requires cost_provenance='computed_from_provider_tokens'."}
    if cost_provenance is None:
        if actual_cents is not None:
            cost_provenance = "provider_reported"
        elif priced_actual_cents is not None:
            cost_provenance = "computed_from_provider_tokens"
        else:
            cost_provenance = "reservation_estimate"
    if cost_provenance not in _PROVENANCES:
        return {"ok": False, "error": "invalid_provenance", "allowed": sorted(_PROVENANCES)}
    if cost_provenance == "provider_reported" and actual_cents is None:
        return {"ok": False, "error": "provenance_without_actual",
                "detail": "'provider_reported' requires a provider-supplied actual_cents."}
    event = {
        "id": str(uuid.uuid4()),
        "workspace_id": ws,
        "job_id": job_id,
        "approval_id": approval_id,
        "actor": actor,
        "provider": provider,
        "model": model,
        "reasoning_level": reasoning_level,
        "kind": kind,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cents": estimated_cents,
        "actual_cents": actual_cents,
        "priced_actual_cents": priced_actual_cents,
        "cost_provenance": cost_provenance,
        "wallet_credits": wallet_credits,
        "created_at_epoch": int(time.time()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    url = _redis_url()
    if not url:
        return {"ok": False, "error": "ledger_store_unavailable"}
    owns = client is None
    client = client or redis.from_url(url, decode_responses=True)
    try:
        await client.rpush(_list_key(ws), json.dumps(event))
        # settle into running totals (cap accounting) - one guarded atomic
        # step that refuses to run during a rebuild. If a rebuild holds the
        # lock, wait bounded; on expiry DEFER to the rebuild's drain step
        # (fail closed, never settle concurrently with a rewrite). The event
        # is already durable in the list, and the rebuild (or the next one)
        # applies the deferral exactly once.
        spent = _spent_cents(event)
        args: list[str] = []
        for window, value in _windows(job_id).items():
            args += [_field(window, value), str(int(spent or 0))]
        settled = False
        deadline = time.monotonic() + _SETTLE_WAIT_S
        while True:
            done = await client.eval(_LUA_GUARDED_HINCRBY, 2, _totals_key(ws), _rebuild_lock_key(ws), *args)
            if done:
                settled = True
                break
            if time.monotonic() >= deadline:
                break
            await asyncio.sleep(0.1)
        if not settled:
            await client.rpush(_pending_settle_key(ws), json.dumps(event))
    except redis.RedisError as exc:
        return {"ok": False, "error": "ledger_write_failed", "detail": type(exc).__name__}
    finally:
        if owns:
            await client.aclose()
    mirror = await _mirror_usage_event(event)
    if not mirror.get("ok"):
        await _backlog_mirror(event)
        return {"ok": True, "id": event["id"], "event": event,
                "mirror": "backlogged", "mirror_error": mirror.get("error")}
    return {"ok": True, "id": event["id"], "event": event, "mirror": "written"}


async def _mirror_usage_event(event: dict[str, Any], *, http: Any | None = None) -> dict[str, Any]:
    """Durable mirror into buffer_blaster.usage_events (019). The response
    status is CHECKED - a silent 401/500 is a durable-failure signal, not a
    dropped write."""
    base, key = _mirror_env()
    if not (base and key):
        return {"ok": True, "skipped": True}  # Redis-only mode; see AOF note in docs
    payload = {k: v for k, v in event.items() if k != "created_at_epoch"}
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Content-Profile": "buffer_blaster", "Prefer": "resolution=ignore-duplicates,return=minimal"}
    try:
        if http is not None:
            resp = await http("POST", f"{base}/rest/v1/usage_events?on_conflict=id", headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(f"{base}/rest/v1/usage_events?on_conflict=id", headers=headers, json=payload)
    except httpx.HTTPError as exc:
        log.error("usage mirror write failed: %s", type(exc).__name__)
        return {"ok": False, "error": "mirror_unreachable", "detail": type(exc).__name__}
    if getattr(resp, "status_code", 200) >= 300:
        log.error("usage mirror write rejected: status=%s", resp.status_code)
        return {"ok": False, "error": "mirror_rejected", "status": resp.status_code}
    return {"ok": True}


async def _backlog_mirror(event: dict[str, Any]) -> None:
    url = _redis_url()
    if not url:
        return
    client = redis.from_url(url, decode_responses=True)
    try:
        ws = event["workspace_id"]
        await client.sadd(_backlog_key(ws), event["id"])
        await client.set(_backlog_payload_key(ws, event["id"]), json.dumps(event))
    except redis.RedisError:
        log.error("usage mirror backlog write failed", exc_info=True)
    finally:
        await client.aclose()


async def reconcile_mirror(*, workspace_id: str | None = None, client: Any | None = None,
                           http: Any | None = None) -> dict[str, Any]:
    """Provably reconcile: replay the mirror backlog, then rebuild the Redis
    cap totals from the durable mirror (source of truth after a Redis reset).
    Sets the reconciled flag only when both succeed."""
    ws = workspace_id or _workspace_id()
    base, key = _mirror_env()
    if not (base and key):
        return {"ok": False, "error": "mirror_not_configured"}
    if not ws:
        return {"ok": False, "error": "workspace_not_configured"}
    url = _redis_url()
    owns = client is None
    client = client or redis.from_url(url, decode_responses=True)
    try:
        # 1) replay backlog
        replayed, failed = 0, 0
        for event_id in await client.smembers(_backlog_key(ws)):
            raw = await client.get(_backlog_payload_key(ws, event_id))
            if not raw:
                await client.srem(_backlog_key(ws), event_id)
                continue
            event = json.loads(raw)
            mirror = await _mirror_usage_event(event, http=http)
            if mirror.get("ok"):
                await client.srem(_backlog_key(ws), event_id)
                await client.delete(_backlog_payload_key(ws, event_id))
                replayed += 1
            else:
                failed += 1
        remaining = int(await client.scard(_backlog_key(ws)))
        if remaining:
            return {"ok": False, "error": "mirror_still_failing", "replayed": replayed,
                    "failed": failed, "backlog_remaining": remaining}
        # 2) rebuild totals from the durable mirror. M3: quiesce new holds
        # with a lock (check_and_hold fails closed while held), read EVERY
        # row via paginated Content-Range with a count assertion (a truncated
        # read must never rebuild an undercount), and preserve active holds:
        # held amounts are recomputed from the holds hash, never deleted.
        lock_token = str(uuid.uuid4())  # fencing token: renew/release only ours
        got_lock = await client.set(_rebuild_lock_key(ws), lock_token, nx=True,
                                    px=_REBUILD_LOCK_MS)
        if not got_lock:
            return {"ok": False, "error": "rebuild_in_progress"}
        try:
            headers = {"apikey": key, "Authorization": f"Bearer {key}",
                       "Accept-Profile": "buffer_blaster"}
            params = {"workspace_id": f"eq.{ws}",
                      "select": "id,job_id,estimated_cents,actual_cents,priced_actual_cents,created_at"}
            rows: list[dict[str, Any]] = []
            page_size = 1000
            total: int | None = None
            while True:
                paged = {**headers, "Range-Unit": "items",
                         "Range": f"{len(rows)}-{len(rows) + page_size - 1}",
                         "Prefer": "count=exact"}
                # Renew BEFORE the fetch too: one slow page is covered up to a
                # full TTL; a fetch longer than that loses the token and the
                # guarded rewrite below aborts instead of clobbering.
                renewed = await client.eval(_LUA_RENEW, 1, _rebuild_lock_key(ws),
                                            lock_token, str(_REBUILD_LOCK_MS))
                if not renewed:
                    return {"ok": False, "error": "rebuild_lock_lost",
                            "detail": "Fencing token gone mid-rebuild; aborting without rewriting totals."}
                if http is not None:
                    resp = await http("GET", f"{base}/rest/v1/usage_events", headers=paged, params=params)
                else:
                    async with httpx.AsyncClient(timeout=15) as h:
                        resp = await h.get(f"{base}/rest/v1/usage_events", headers=paged, params=params)
                if getattr(resp, "status_code", 200) >= 300:
                    return {"ok": False, "error": "mirror_read_failed", "status": resp.status_code}
                content_range = str(getattr(resp, "headers", {}) .get("content-range", "") or "")
                # PostgREST exact count: "0-999/1234" or "*/1234".
                total_header = content_range.split("/")[-1] if "/" in content_range else ""
                try:
                    total = int(total_header)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "mirror_count_unknown",
                            "detail": "PostgREST did not return an exact Content-Range total; refusing to rebuild from an unbounded read."}
                batch = resp.json() or []
                rows.extend(batch)
                # Renew the fenced lock between pages: a slow multi-page read
                # must never outlive its TTL mid-rewrite. If our token is
                # gone, someone else owns the lock - abort, don't rewrite.
                renewed = await client.eval(_LUA_RENEW, 1, _rebuild_lock_key(ws),
                                            lock_token, str(_REBUILD_LOCK_MS))
                if not renewed:
                    return {"ok": False, "error": "rebuild_lock_lost",
                            "detail": "Fencing token gone mid-rebuild; aborting without rewriting totals."}
                if len(rows) >= total or not batch:
                    break
            if len(rows) != total:
                return {"ok": False, "error": "mirror_count_mismatch",
                        "expected": total, "fetched": len(rows)}
            # Deferred releases first (idempotent HDEL): the held_sums
            # recompute below then reflects the post-release state, and the
            # commit LTRIMs exactly this captured prefix.
            release_raw = await client.lrange(_release_queue_key(ws), 0, -1)
            released_count = 0
            for hold_id in release_raw:
                if hold_id and await client.hdel(_holds_key(ws), str(hold_id)):
                    released_count += 1
            # Active holds survive the rebuild (recomputed from the holds hash).
            held_sums: dict[str, int] = {}
            for raw_hold in (await client.hgetall(_holds_key(ws))).values():
                try:
                    held = json.loads(raw_hold)
                    est = int(held.get("est_cents") or 0)
                    for window, value in (held.get("windows") or {}).items():
                        key_f = _field(window, value, held=True)
                        held_sums[key_f] = held_sums.get(key_f, 0) + est
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
            # Fold every increment (mirror rows + held sums + deferred-settle
            # drain) into one atomic token-checked Lua rewrite. Deferred
            # settles are durable in the event list but may have missed the
            # mirror read; each is applied exactly once here, inside the
            # lock, skipping any event the mirror read already covered.
            increments: dict[str, int] = {}
            for row in rows:
                cents = _spent_cents(row)
                if not cents:
                    continue
                day = str(row.get("created_at", ""))[:10]
                month = day[:7]
                increments[_field("day", day)] = increments.get(_field("day", day), 0) + int(cents)
                increments[_field("month", month)] = increments.get(_field("month", month), 0) + int(cents)
                if row.get("job_id"):
                    jf = _field("job", str(row["job_id"]))
                    increments[jf] = increments.get(jf, 0) + int(cents)
            for held_field, amount in held_sums.items():
                increments[held_field] = increments.get(held_field, 0) + amount
            drained = 0
            mirrored_ids = {str(row.get("id")) for row in rows}
            pending_raw = await client.lrange(_pending_settle_key(ws), 0, -1)
            for raw_pending in pending_raw:
                try:
                    pending = json.loads(raw_pending)
                    cents = _spent_cents(pending)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if not cents or str(pending.get("id")) in mirrored_ids:
                    continue  # already settled by the mirror read: exactly once
                for window, value in _windows(pending.get("job_id"),
                                              time.gmtime(pending.get("created_at_epoch", time.time()))).items():
                    wf = _field(window, value)
                    increments[wf] = increments.get(wf, 0) + int(cents)
                drained += 1
            argv: list[str] = [lock_token, str(len(pending_raw)), str(len(release_raw))]
            for field_name, delta in increments.items():
                argv.extend([field_name, str(delta)])
            argv.append(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            committed = await client.eval(_LUA_GUARDED_REWRITE, 5,
                                          _rebuild_lock_key(ws), _totals_key(ws),
                                          _pending_settle_key(ws), _reconciled_key(ws),
                                          _release_queue_key(ws), *argv)
            if not committed:
                return {"ok": False, "error": "rebuild_lock_lost",
                        "detail": "Fencing token lost before the totals commit; aborted atomically, totals untouched."}
            return {"ok": True, "replayed": replayed, "rows_reconciled": len(rows),
                    "holds_preserved": len(held_sums), "deferred_settles_applied": drained,
                    "deferred_releases_applied": released_count, "backlog_remaining": 0}
        finally:
            # fenced release: only our token's lock is removed
            await client.eval(_LUA_RELEASE_LOCK, 1, _rebuild_lock_key(ws), lock_token)
    except redis.RedisError as exc:
        return {"ok": False, "error": "ledger_store_unavailable", "detail": type(exc).__name__}
    finally:
        if owns:
            await client.aclose()


async def list_events(*, workspace_id: str | None = None, client: Any | None = None) -> list[dict[str, Any]]:
    ws = workspace_id or _workspace_id()
    if not ws:
        return []
    url = _redis_url()
    if not url:
        return []
    owns = client is None
    client = client or redis.from_url(url, decode_responses=True)
    try:
        raw = await client.lrange(_list_key(ws), 0, -1)
        out = []
        for line in raw:
            try:
                out.append(json.loads(line))
            except (TypeError, json.JSONDecodeError):
                continue
        return out
    except redis.RedisError:
        return []
    finally:
        if owns:
            await client.aclose()


_PROVENANCES = {"provider_reported", "computed_from_provider_tokens", "reservation_estimate"}


def _spent_cents(event: dict[str, Any]) -> int:
    """What an event counts against caps (M1): provider actual when reported;
    otherwise the labeled token-priced actual computed from provider token
    counts at the configured vendor price; otherwise the conservative
    reservation (estimate) stays in cap totals forever - an unknown cost
    never settles below its proven upper bound."""
    if event.get("actual_cents") is not None:
        return int(event["actual_cents"])
    if event.get("priced_actual_cents") is not None:
        return int(event["priced_actual_cents"])
    return int(event.get("estimated_cents") or 0)


async def check_caps(
    *,
    job_id: str | None,
    additional_estimated_cents: int,
    workspace_id: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Advisory pre-flight read of caps (the enforcement path is
    check_and_hold, which is atomic). Fails closed on invalid config."""
    ws = workspace_id or _workspace_id()
    caps = await read_caps()
    if not caps.get("ok"):
        return caps
    cap_values = caps["caps"]
    if not any(cap_values.values()):
        return {"ok": True, "caps_configured": False}
    events = await list_events(workspace_id=ws, client=client)
    add = max(0, int(additional_estimated_cents))
    now = time.gmtime()
    day = time.strftime("%Y-%m-%d", now)
    month = time.strftime("%Y-%m", now)
    job_cap = cap_values["USAGE_CAP_JOB_CENTS"]
    daily_cap = cap_values["USAGE_CAP_DAILY_CENTS"]
    monthly_cap = cap_values["USAGE_CAP_MONTHLY_CENTS"]
    if job_cap and job_id:
        spent = sum(_spent_cents(e) for e in events if e.get("job_id") == job_id)
        if spent + add > job_cap:
            return {"ok": False, "error": "job_cap_exceeded", "job_id": job_id,
                    "job_spent_cents": spent, "job_cap_cents": job_cap,
                    "additional_estimated_cents": add}
    if daily_cap:
        spent = sum(_spent_cents(e) for e in events if str(e.get("created_at", "")).startswith(day))
        if spent + add > daily_cap:
            return {"ok": False, "error": "workspace_cap_exceeded", "window": "daily",
                    "workspace_spent_cents": spent, "workspace_cap_cents": daily_cap,
                    "additional_estimated_cents": add}
    if monthly_cap:
        spent = sum(_spent_cents(e) for e in events if str(e.get("created_at", "")).startswith(month))
        if spent + add > monthly_cap:
            return {"ok": False, "error": "workspace_cap_exceeded", "window": "monthly",
                    "workspace_spent_cents": spent, "workspace_cap_cents": monthly_cap,
                    "additional_estimated_cents": add}
    return {"ok": True, "caps_configured": True}


_GROUP_KEYS = {"day", "model", "job", "agent"}


def _group_key(event: dict[str, Any], group_by: str) -> str:
    if group_by == "day":
        return str(event.get("created_at", ""))[:10]
    if group_by == "model":
        return str(event.get("model") or "")
    if group_by == "job":
        return str(event.get("job_id") or "")
    return str(event.get("actor") or "")


async def usage_report(*, group_by: str = "day", workspace_id: str | None = None,
                       client: Any | None = None) -> dict[str, Any]:
    if group_by not in _GROUP_KEYS:
        return {"ok": False, "error": "invalid_group_by", "allowed": sorted(_GROUP_KEYS)}
    events = await list_events(workspace_id=workspace_id, client=client)
    groups: dict[str, dict[str, Any]] = {}
    for e in events:
        key = _group_key(e, group_by)
        row = groups.setdefault(key, {"group": key, "events": 0,
                                      "estimated_cents": 0, "actual_cents": 0,
                                      "actual_reported_events": 0,
                                      "tokens_in": 0, "tokens_out": 0,
                                      "wallet_credits": 0})
        row["events"] += 1
        row["estimated_cents"] += int(e.get("estimated_cents") or 0)
        if e.get("actual_cents") is not None:
            row["actual_cents"] += int(e["actual_cents"])
            row["actual_reported_events"] += 1
        row["tokens_in"] += int(e.get("tokens_in") or 0)
        row["tokens_out"] += int(e.get("tokens_out") or 0)
        row["wallet_credits"] += int(e.get("wallet_credits") or 0)
    rows = [groups[k] for k in sorted(groups, reverse=True)]
    return {"ok": True, "group_by": group_by, "rows": rows,
            "totals": {
                "events": sum(r["events"] for r in rows),
                "estimated_cents": sum(r["estimated_cents"] for r in rows),
                "actual_cents": sum(r["actual_cents"] for r in rows),
                "actual_reported_events": sum(r["actual_reported_events"] for r in rows),
            }}
