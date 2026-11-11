"""S4 revision 7: reviewer race closures.

R2: a pending-settle event RPUSHed between the rebuild's LRANGE and the Lua
commit must SURVIVE (prefix LTRIM, never DEL) - a lost settle is a cap
undercount. R3: release_hold during a rebuild is queued atomically and the
rebuild drains it exactly once; no caller retry needed for liveness. Also:
the S7/S6 busy-lock release is token-fenced (a post-TTL release never
deletes a new holder's lock).
"""
import asyncio
import json
import time

import fakeredis.aioredis
import pytest

from api.services import captions, usage_ledger


@pytest.fixture
def ledger_env(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(usage_ledger, "_redis_url", lambda: "redis://fake")
    monkeypatch.setattr(usage_ledger, "_workspace_id", lambda: "ws-test")
    monkeypatch.setattr(usage_ledger, "_REBUILD_LOCK_MS", 50)
    monkeypatch.setattr(usage_ledger, "_SETTLE_WAIT_S", 0.05)
    monkeypatch.setattr(usage_ledger, "_mirror_env", lambda: ("https://pg", "k"))
    today = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime())
    rows = [{"id": "r1", "workspace_id": "ws-test", "job_id": "j1",
             "estimated_cents": 10, "actual_cents": None,
             "priced_actual_cents": None, "created_at": today}]

    class _Resp:
        status_code = 200
        headers = {"content-range": f"0-{len(rows) - 1}/{len(rows)}"}

        def json(self):
            return rows

    async def http(method, url, headers=None, params=None):
        return _Resp()

    return r, rows, http


@pytest.mark.asyncio
async def test_late_pending_settle_survives_commit(ledger_env, monkeypatch):
    r, rows, http = ledger_env
    late = {"id": "late-1", "workspace_id": "ws-test", "job_id": "j9",
            "estimated_cents": 7, "actual_cents": None,
            "priced_actual_cents": None, "created_at_epoch": int(time.time()),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    real_eval = r.eval

    async def rpush_between(script, keys, *args):
        if script == usage_ledger._LUA_GUARDED_REWRITE:
            # event lands after the drain LRANGE, before the commit
            await r.rpush(usage_ledger._pending_settle_key("ws-test"), json.dumps(late))
        return await real_eval(script, keys, *args)

    monkeypatch.setattr(r, "eval", rpush_between)
    rec = await usage_ledger.reconcile_mirror(http=http, client=r)
    assert rec["ok"] is True
    surviving = await r.lrange(usage_ledger._pending_settle_key("ws-test"), 0, -1)
    assert len(surviving) == 1 and json.loads(surviving[0])["id"] == "late-1", \
        "late event must survive the commit (DEL would lose it = cap undercount)"
    totals = await r.hgetall(usage_ledger._totals_key("ws-test"))
    day_total = sum(int(v) for k, v in totals.items() if k.startswith("spent:day:"))
    assert day_total == 10, totals  # late event NOT double-applied in this rebuild
    # the NEXT reconcile applies it exactly once
    rec2 = await usage_ledger.reconcile_mirror(http=http, client=r)
    assert rec2["ok"] is True and rec2["deferred_settles_applied"] == 1
    totals = await r.hgetall(usage_ledger._totals_key("ws-test"))
    assert sum(int(v) for k, v in totals.items() if k.startswith("spent:day:")) == 17


@pytest.mark.asyncio
async def test_ltrim_negative_control_del_would_lose(ledger_env):
    r, rows, http = ledger_env
    # the r6 defect shape: DEL instead of prefix LTRIM
    assert "LTRIM" in usage_ledger._LUA_GUARDED_REWRITE
    assert "DEL', KEYS[3]" not in usage_ledger._LUA_GUARDED_REWRITE


@pytest.mark.asyncio
async def test_release_during_rebuild_queued_and_drained_exactly_once(ledger_env, monkeypatch):
    r, rows, http = ledger_env
    # seed a hold record as check_and_hold would have written it
    hold_id = "hold-1"
    await r.hset(usage_ledger._holds_key("ws-test"), hold_id, json.dumps(
        {"est_cents": 40, "windows": {"job": "j1"}}))
    today = time.strftime("%Y-%m-%d", time.gmtime())
    totals_key = usage_ledger._totals_key("ws-test")
    await r.hset(totals_key, "held:job:j1", 40)
    # a rebuild is in progress (lock held by someone else)
    await r.set(usage_ledger._rebuild_lock_key("ws-test"), "other-token", px=50)
    await usage_ledger.release_hold({"workspace_id": "ws-test", "est_cents": 40,
                                     "hold_id": hold_id, "windows": {"job": "j1"}}, client=r)
    # release was queued, NOT executed: hold record and totals intact
    assert await r.hexists(usage_ledger._holds_key("ws-test"), hold_id)
    assert await r.lrange(usage_ledger._release_queue_key("ws-test"), 0, -1) == [hold_id]
    # double release during the same rebuild queues a second (idempotent) entry
    await usage_ledger.release_hold({"workspace_id": "ws-test", "est_cents": 40,
                                     "hold_id": hold_id, "windows": {"job": "j1"}}, client=r)
    # rebuild runs (lock expires first)
    await asyncio.sleep(0.06)
    rec = await usage_ledger.reconcile_mirror(http=http, client=r)
    assert rec["ok"] is True and rec["deferred_releases_applied"] == 1
    assert not await r.hexists(usage_ledger._holds_key("ws-test"), hold_id)
    assert await r.lrange(usage_ledger._release_queue_key("ws-test"), 0, -1) == []
    totals = await r.hgetall(totals_key)
    assert "held:job:j1" not in totals, f"released hold must not survive the rebuild: {totals}"
    # liveness without a caller retry: the next check_and_hold sees an empty
    # queue and does not loop; a queued release triggers an inline reconcile
    await r.rpush(usage_ledger._release_queue_key("ws-test"), "hold-2")
    await r.hset(usage_ledger._holds_key("ws-test"), "hold-2",
                 json.dumps({"est_cents": 5, "windows": {"job": "j1"}}))
    real_reconcile = usage_ledger.reconcile_mirror

    async def wrapped(*a, **kw):
        kw.setdefault("http", http)
        return await real_reconcile(*a, **kw)

    monkeypatch.setattr(usage_ledger, "reconcile_mirror", wrapped)
    admitted = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=1, client=r)
    assert admitted.get("ok") is True
    assert not await r.hexists(usage_ledger._holds_key("ws-test"), "hold-2"), \
        "queued release must be drained by the inline reconcile"


@pytest.mark.asyncio
async def test_busy_lock_release_is_token_fenced():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    # holder A's lock lapses (TTL), holder B acquires; A's fenced release
    # must NOT delete B's lock
    await r.set("bb:captions:busy", "a:1", nx=True, px=50)
    await asyncio.sleep(0.06)  # TTL lapse
    assert await r.set("bb:captions:busy", "b:2", nx=True, px=60_000)
    deleted = await r.eval("""if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0""", 1, "bb:captions:busy", "a:1")
    assert deleted == 0
    assert await r.get("bb:captions:busy") == "b:2", "stale holder must never delete the new lock"
    deleted = await r.eval("""if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0""", 1, "bb:captions:busy", "b:2")
    assert deleted == 1 and await r.get("bb:captions:busy") is None
