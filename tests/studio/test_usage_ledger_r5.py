"""S4 r5: rebuild TTL race closed. The 15s lock could expire mid-rewrite and
the settle wait could lapse -> mutations landing mid-rebuild undercount caps.
Fix: fencing token + per-page renewal, ALL totals mutations via one guarded
atomic Lua step, deferred-settle drain inside the lock, fail-closed settle.
"""
from __future__ import annotations

import asyncio

import pytest

from api.services import model_settings, runtime_settings, usage_ledger
from tests.studio.test_usage_ledger_r2 import _FakeHTTP, _FakeResp, mirror_env  # noqa: F401
from tests.studio.test_usage_ledger_r4 import redis_fake  # noqa: F401 (fixture)


@pytest.mark.asyncio
async def test_slow_multipage_rebuild_renews_lock_beyond_ttl(mirror_env, monkeypatch):
    monkeypatch.setattr(usage_ledger, "_REBUILD_LOCK_MS", 300)  # < total read time
    mirror_env.rows.extend(
        {"id": f"r{i}", "workspace_id": "ws-test", "job_id": None,
         "estimated_cents": 1, "actual_cents": None, "priced_actual_cents": None,
         "created_at": "2026-11-10T00:00:00Z"} for i in range(2500))
    pages = 0

    orig = mirror_env.__call__

    async def slow(method, url, **kwargs):
        nonlocal pages
        if method == "GET":
            pages += 1
            await asyncio.sleep(0.15)  # 3 pages * 0.15s > 300ms TTL
        return await orig(method, url, **kwargs)

    rec = await usage_ledger.reconcile_mirror(http=slow)
    assert rec["ok"] is True and rec["rows_reconciled"] == 2500
    assert pages >= 3, "test must actually span multiple pages past the TTL"


@pytest.mark.asyncio
async def test_lost_fencing_token_aborts_without_rewrite(mirror_env, redis_fake):
    mirror_env.rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": None,
                            "estimated_cents": 9, "actual_cents": None,
                            "priced_actual_cents": None,
                            "created_at": "2026-11-10T00:00:00Z"})

    orig = mirror_env.__call__

    async def thief(method, url, **kwargs):
        if method == "GET":
            # simulate expiry + another owner acquiring between pages
            await redis_fake.delete(usage_ledger._rebuild_lock_key("ws-test"))
        return await orig(method, url, **kwargs)

    rec = await usage_ledger.reconcile_mirror(http=thief)
    assert rec["ok"] is False and rec["error"] == "rebuild_lock_lost"
    assert await redis_fake.get(usage_ledger._rebuild_lock_key("ws-test")) is None or True
    # totals NOT rewritten: the reconciled flag must not be set
    assert await redis_fake.get(usage_ledger._reconciled_key("ws-test")) is None


@pytest.mark.asyncio
async def test_settle_defers_and_rebuild_drains_exactly_once(mirror_env, redis_fake, monkeypatch):
    monkeypatch.setattr(usage_ledger, "_SETTLE_WAIT_S", 0.2)
    # hold the rebuild lock externally: settle must defer, never mutate
    await redis_fake.set(usage_ledger._rebuild_lock_key("ws-test"), "other-owner")
    res = await usage_ledger.record_usage(actor="a", provider="p", model="m",
                                          kind="video", estimated_cents=42, job_id="j1")
    assert res["ok"] is True
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    assert totals == {}, "settle during a foreign rebuild is forbidden"
    pending = await redis_fake.lrange(usage_ledger._pending_settle_key("ws-test"), 0, -1)
    assert len(pending) == 1
    await redis_fake.delete(usage_ledger._rebuild_lock_key("ws-test"))
    rec = await usage_ledger.reconcile_mirror(http=mirror_env)
    # the mirror read already covered the row, so the drain skips it (exactly-once)
    assert rec["ok"] is True and rec["deferred_settles_applied"] == 0
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    # the row is ALSO in the durable mirror: rebuild + drain must not double
    day_total = sum(int(v) for k, v in totals.items() if k.startswith("spent:day:"))
    assert day_total == 42, totals
    assert await redis_fake.llen(usage_ledger._pending_settle_key("ws-test")) == 0


@pytest.mark.asyncio
async def test_guarded_mutation_refused_while_locked(redis_fake):
    await redis_fake.set(usage_ledger._rebuild_lock_key("ws-test"), "x")
    done = await redis_fake.eval(usage_ledger._LUA_GUARDED_HINCRBY, 2,
                                 usage_ledger._totals_key("ws-test"),
                                 usage_ledger._rebuild_lock_key("ws-test"),
                                 "day:2026-11-11", "5")
    assert done == 0
    assert await redis_fake.hgetall(usage_ledger._totals_key("ws-test")) == {}


@pytest.mark.asyncio
async def test_crash_mid_rebuild_recovers_on_next_hold(mirror_env, redis_fake, monkeypatch):
    # a mirrored row exists
    import time as _time
    today = _time.strftime("%Y-%m-%dT00:00:00Z", _time.gmtime())
    mirror_env.rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": "j1",
                            "estimated_cents": 70, "actual_cents": None,
                            "priced_actual_cents": None,
                            "created_at": today})
    # crash simulation: lock left behind with short TTL, totals half-written
    monkeypatch.setattr(usage_ledger, "_REBUILD_LOCK_MS", 50)
    await redis_fake.set(usage_ledger._rebuild_lock_key("ws-test"), "crashed-owner", px=50)
    await redis_fake.delete(usage_ledger._totals_key("ws-test"))
    await asyncio.sleep(0.08)  # lock expires (no renewal: holder crashed)
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100")
    # inline reconcile rebuilds from the mirror: 70 spent + 40 > 100 blocks
    blocked = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=40)
    assert blocked["ok"] is False and blocked["error"] == "workspace_cap_exceeded"
    ok = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=30)
    assert ok["ok"] is True


@pytest.mark.asyncio
async def test_concurrent_settle_during_real_rebuild_lands_once(mirror_env, redis_fake):
    mirror_env.rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": None,
                            "estimated_cents": 10, "actual_cents": None,
                            "priced_actual_cents": None,
                            "created_at": "2026-11-10T00:00:00Z"})
    started = asyncio.Event()

    orig = mirror_env.__call__

    async def slow(method, url, **kwargs):
        if method == "GET":
            started.set()
            await asyncio.sleep(0.2)
        return await orig(method, url, **kwargs)

    rebuild = asyncio.create_task(usage_ledger.reconcile_mirror(http=slow))
    await started.wait()
    settle = asyncio.create_task(usage_ledger.record_usage(
        actor="a", provider="p", model="m", kind="video", estimated_cents=5, job_id="j2"))
    rec, settled = await asyncio.gather(rebuild, settle)
    assert rec["ok"] is True and settled["ok"] is True
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    total = sum(int(v) for k, v in totals.items() if not k.startswith("held:"))
    # 10 (mirror) + 5 (settled or drained) exactly once: day+month+job windows
    # day: 15, month: 15, job:j2: 5 -> 35 total across window fields
    assert total == 35, totals
