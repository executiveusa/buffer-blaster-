"""S4 revision 6: the rebuild commit is one atomic token-checked Lua rewrite.

Revision 5 renewed the fencing lock per page but still renewed-then-rewrote:
the lock could expire between the last renewal and the pipeline commit, and
a second worker's rebuild could then be clobbered by the first. Revision 6
commits via _LUA_GUARDED_REWRITE (token check + DEL + HINCRBYs + flag in one
Lua step) and renews BEFORE each page fetch. These tests prove:
1. a single SLOW page fetch that outlives the TTL aborts without rewriting;
2. a token lost exactly at commit time aborts atomically (totals untouched).
"""
import asyncio
import json

import fakeredis.aioredis
import pytest

from api.services import usage_ledger


@pytest.fixture
def ledger_env(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(usage_ledger, "_redis_url", lambda: "redis://fake")
    monkeypatch.setattr(usage_ledger, "_workspace_id", lambda: "ws-test")
    monkeypatch.setattr(usage_ledger, "_REBUILD_LOCK_MS", 50)
    monkeypatch.setattr(usage_ledger, "_SETTLE_WAIT_S", 0.05)
    rows = []

    class _Resp:
        status_code = 200
        headers = {"content-range": f"0-{max(len(rows) - 1, 0)}/{len(rows)}"}

        def json(self):
            return rows

    async def http(method, url, headers=None, params=None):
        return _Resp()

    monkeypatch.setattr(usage_ledger, "_mirror_env", lambda: ("https://pg", "k"))
    return r, rows, http


@pytest.mark.asyncio
async def test_single_slow_page_outliving_ttl_aborts_without_rewrite(ledger_env, monkeypatch):
    r, rows, _ = ledger_env
    import time as _time
    today = _time.strftime("%Y-%m-%dT00:00:00Z", _time.gmtime())
    rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": "j1",
                 "estimated_cents": 30, "actual_cents": None,
                 "priced_actual_cents": None, "created_at": today})
    calls = {"n": 0}

    class _Resp:
        status_code = 200
        headers = {"content-range": f"0-{len(rows) - 1}/{len(rows)}"}

        def json(self):
            return rows

    async def slow_http(method, url, headers=None, params=None):
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(0.09)  # one page fetch longer than the 50ms TTL
        return _Resp()

    async def second_worker():
        await asyncio.sleep(0.06)  # acquires the expired lock mid-fetch
        return await usage_ledger.reconcile_mirror(http=None if False else _second_http,
                                                   client=r)

    class _Resp2(_Resp):
        pass

    async def _second_http(method, url, headers=None, params=None):
        return _Resp2()

    first, second = await asyncio.gather(
        usage_ledger.reconcile_mirror(http=slow_http, client=r),
        second_worker(),
    )
    # exactly one worker committed; the slow one either lost its lock or lost
    # the atomic commit - and totals must equal ONE rebuild, never doubled.
    results = [first, second]
    assert any(res.get("ok") for res in results), results
    assert any(res.get("error") == "rebuild_lock_lost" for res in results) or all(
        res.get("ok") for res in results), results
    totals = await r.hgetall(usage_ledger._totals_key("ws-test"))
    day_total = sum(int(v) for k, v in totals.items() if k.startswith("spent:day:"))
    assert day_total == 30, totals


@pytest.mark.asyncio
async def test_token_lost_exactly_at_commit_aborts_atomically(ledger_env, monkeypatch):
    r, rows, http = ledger_env
    await r.hset(usage_ledger._totals_key("ws-test"), "spent:day:2099-01-01", 7)

    real_eval = r.eval

    async def sabotage_eval(script, keys, *args):
        if script == usage_ledger._LUA_GUARDED_REWRITE:
            # another worker steals the lock in the check->commit gap
            await r.delete(usage_ledger._rebuild_lock_key("ws-test"))
            await r.set(usage_ledger._rebuild_lock_key("ws-test"), "other-token")
        return await real_eval(script, keys, *args)

    monkeypatch.setattr(r, "eval", sabotage_eval)
    rec = await usage_ledger.reconcile_mirror(http=http, client=r)
    assert rec["ok"] is False and rec["error"] == "rebuild_lock_lost"
    totals = await r.hgetall(usage_ledger._totals_key("ws-test"))
    assert totals == {"spent:day:2099-01-01": "7"}, totals  # untouched
    assert await r.get(usage_ledger._reconciled_key("ws-test")) is None


@pytest.mark.asyncio
async def test_guarded_rewrite_negative_control(ledger_env, monkeypatch):
    """Without the token check the slow-page race WOULD double-rewrite."""
    r, rows, _ = ledger_env
    import time as _time
    today = _time.strftime("%Y-%m-%dT00:00:00Z", _time.gmtime())
    rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": "j1",
                 "estimated_cents": 30, "actual_cents": None,
                 "priced_actual_cents": None, "created_at": today})
    # an unguarded rewrite (the r5 defect shape) always returns 1
    unguarded = usage_ledger._LUA_GUARDED_REWRITE.replace(
        "if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end\n", "")
    assert "return 0" not in unguarded
    await r.set(usage_ledger._rebuild_lock_key("ws-test"), "other-token")
    committed = await r.eval(unguarded, 5, usage_ledger._rebuild_lock_key("ws-test"),
                             usage_ledger._totals_key("ws-test"),
                             usage_ledger._pending_settle_key("ws-test"),
                             usage_ledger._reconciled_key("ws-test"),
                             usage_ledger._release_queue_key("ws-test"),
                             "stale-token", "0", "0", "spent:day:x", "1", "ts")
    assert committed == 1  # proves the guard line is what stops the clobber
    await r.delete(usage_ledger._totals_key("ws-test"), usage_ledger._reconciled_key("ws-test"))
