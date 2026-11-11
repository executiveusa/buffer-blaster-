"""S4 r4: reviewer money defects M1/M2/M3.
M1: ceil(chars/4) was not an input-token upper bound (CJK/emoji/code
    undercount); provider usage without cost settled caps at an underestimate
    forever. Now: proven UTF-8 byte bound + separately-labeled priced actuals;
    unknown cost keeps the full reservation. Provider actuals are never
    falsified.
M2: hold release is idempotent by unique hold_id (double/concurrent release
    is a no-op).
M3: reconcile paginates with an exact-count assertion, preserves active
    holds, and quiesces new holds during the rebuild.

Fixtures use one shared fakeredis SERVER with a fresh CONNECTION per call,
so WATCH/MULTI concurrency semantics are real (per-connection watch state).
"""
from __future__ import annotations

import asyncio

import fakeredis
import pytest

from api.services import llm_adapter, model_settings, runtime_settings, usage_ledger
from tests.studio.test_usage_ledger_r2 import _FakeHTTP, _FakeResp, mirror_env  # noqa: F401 (pytest fixture)


@pytest.fixture
def redis_fake(monkeypatch):
    server = fakeredis.FakeServer()

    def factory(*a, **k):
        return fakeredis.FakeAsyncRedis(server=server, decode_responses=True)

    monkeypatch.setattr(usage_ledger.redis, "from_url", factory)
    monkeypatch.setattr(model_settings.redis, "from_url", factory)
    monkeypatch.setattr(runtime_settings.redis, "from_url", factory)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    for k in usage_ledger._CAP_KEYS:
        monkeypatch.delenv(k, raising=False)
    return factory()


# ---------------------------------------------------------------- M1: bound


def test_byte_bound_counts_cjk_emoji_code_conservatively():
    cjk = "日本語のテキストです" * 10          # 100 chars, 300 bytes
    emoji = "😀" * 50                              # 50 chars, 200 bytes
    code = "a=b+c*d/e; " * 40                       # dense ASCII
    for text in (cjk, emoji, code):
        bound = llm_adapter.estimate_input_tokens(text, "")
        assert bound >= len(text.encode("utf-8"))
    # regression guard vs the removed formula: CJK was undercounted >3x
    assert llm_adapter.estimate_input_tokens(cjk, "") > (len(cjk) // 4) * 3


def test_estimate_uses_byte_bound_not_char_quarters(monkeypatch):
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_IN_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_OUT_CENTS_PER_MTOK", "1500")
    cjk = "漢字" * 100  # 200 chars / 600 bytes
    est = llm_adapter.estimate_llm_cents("anthropic", "claude-x", cjk, "", 100)
    est_in = llm_adapter.estimate_input_tokens(cjk, "")
    assert est_in == 600 + llm_adapter.TOKEN_BOUND_OVERHEAD
    assert est == -(-(est_in * 300 + 100 * 1500) // 1_000_000)  # exact ceil


# ------------------------------------------------------- M1: priced actuals


@pytest.mark.asyncio
async def test_tokens_without_cost_record_priced_actual_labeled(redis_fake, monkeypatch):
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_IN_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_OUT_CENTS_PER_MTOK", "1500")
    monkeypatch.setenv("ACTIVE_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-x")

    async def fake_anthropic(prompt, system, max_tokens, key, model):
        return "ok", {"tokens_in": 1000, "tokens_out": 2000}  # no cost field

    monkeypatch.setattr(llm_adapter, "_anthropic", fake_anthropic)
    await llm_adapter.chat("hello", actor="tester")
    events = await usage_ledger.list_events()
    assert len(events) == 1
    ev = events[0]
    assert ev["actual_cents"] is None, "provider actuals-only: never falsified"
    assert ev["priced_actual_cents"] == llm_adapter.priced_actual_cents(
        "anthropic", "claude-x", 1000, 2000) == -(-(1000 * 300 + 2000 * 1500) // 1_000_000)
    assert ev["cost_provenance"] == "computed_from_provider_tokens"
    assert usage_ledger._spent_cents(ev) == ev["priced_actual_cents"]


@pytest.mark.asyncio
async def test_unknown_cost_keeps_full_reservation_in_caps(redis_fake, monkeypatch):
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_IN_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("LLM_PRICE_ANTHROPIC_CLAUDE_X_OUT_CENTS_PER_MTOK", "1500")
    monkeypatch.setenv("ACTIVE_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-x")

    async def fake_anthropic_no_usage(prompt, system, max_tokens, key, model):
        return "ok", {"tokens_in": None, "tokens_out": None}

    monkeypatch.setattr(llm_adapter, "_anthropic", fake_anthropic_no_usage)
    await llm_adapter.chat("hello", actor="tester")
    events = await usage_ledger.list_events()
    ev = events[0]
    assert ev["actual_cents"] is None and ev["priced_actual_cents"] is None
    assert ev["cost_provenance"] == "reservation_estimate"
    # the full conservative reservation stays in cap totals (no settle-down)
    assert usage_ledger._spent_cents(ev) == ev["estimated_cents"]


@pytest.mark.asyncio
async def test_record_usage_rejects_mixed_or_unlabeled_priced(redis_fake):
    bad = await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="llm",
                                          estimated_cents=10, actual_cents=5,
                                          priced_actual_cents=4,
                                          cost_provenance="computed_from_provider_tokens")
    assert bad["ok"] is False and bad["error"] == "cost_fields_mixed"
    bad2 = await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="llm",
                                           priced_actual_cents=4)
    assert bad2["ok"] is False and bad2["error"] == "provenance_required"
    bad3 = await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="llm",
                                           estimated_cents=10,
                                           cost_provenance="provider_reported")
    assert bad3["ok"] is False and bad3["error"] == "provenance_without_actual"


# ----------------------------------------------------------- M2: hold ids


@pytest.mark.asyncio
async def test_double_release_is_noop(redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "1000")
    res = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=100)
    assert res["ok"] is True
    hold = res["hold"]
    assert hold["hold_id"]
    totals_key = usage_ledger._totals_key("ws-test")
    day_field = next(f for f in await redis_fake.hkeys(totals_key) if f.startswith("held:"))
    assert int(await redis_fake.hget(totals_key, day_field)) == 100
    await usage_ledger.release_hold(hold)
    assert int(await redis_fake.hget(totals_key, day_field) or 0) == 0
    await usage_ledger.release_hold(hold)  # second release: must not go negative
    assert int(await redis_fake.hget(totals_key, day_field) or 0) == 0


@pytest.mark.asyncio
async def test_concurrent_double_release_decrements_once(redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "1000")
    res = await usage_ledger.check_and_hold(job_id="j1", estimated_cents=100)
    hold = res["hold"]
    await asyncio.gather(*(usage_ledger.release_hold(hold) for _ in range(8)))
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    held_values = [int(v) for k, v in totals.items() if k.startswith("held:")]
    assert held_values and all(v == 0 for v in held_values), f"held went negative: {totals}"
    assert await redis_fake.hgetall(usage_ledger._holds_key("ws-test")) == {}


# ------------------------------------------------------- M3: reconcile


@pytest.mark.asyncio
async def test_reconcile_paginates_and_asserts_exact_count(mirror_env):
    mirror_env.rows.extend(
        {"id": f"r{i}", "workspace_id": "ws-test", "job_id": "j1",
         "estimated_cents": 1, "actual_cents": None, "priced_actual_cents": None,
         "created_at": "2026-11-10T00:00:00Z"} for i in range(2500))
    rec = await usage_ledger.reconcile_mirror(http=mirror_env)
    assert rec["ok"] is True and rec["rows_reconciled"] == 2500
    gets = [c for c in mirror_env.calls if c[0] == "GET"]
    assert len(gets) >= 3, "must paginate the durable mirror"


class _TruncatingHTTP(_FakeHTTP):
    """PostgREST that claims 5 total rows but stops delivering after 2."""

    async def __call__(self, method, url, **kwargs):
        if method == "GET":
            headers = kwargs.get("headers") or {}
            start = int(headers.get("Range", "0-0").split("-", 1)[0])
            if start == 0:
                return _FakeResp(200, self.rows[:2],
                                 headers={"content-range": "0-1/5"})
            return _FakeResp(200, [], headers={"content-range": f"{start}-{start}/5"})
        return await super().__call__(method, url, **kwargs)


@pytest.mark.asyncio
async def test_reconcile_rejects_truncated_read(mirror_env):
    http = _TruncatingHTTP()
    http.rows.extend({"id": f"r{i}", "workspace_id": "ws-test", "job_id": None,
                      "estimated_cents": 1, "actual_cents": None,
                      "created_at": "2026-11-10T00:00:00Z"} for i in range(2))
    rec = await usage_ledger.reconcile_mirror(http=http)
    assert rec["ok"] is False and rec["error"] == "mirror_count_mismatch"
    assert rec["expected"] == 5 and rec["fetched"] == 2


class _NoCountHTTP(_FakeHTTP):
    async def __call__(self, method, url, **kwargs):
        resp = await super().__call__(method, url, **kwargs)
        if method == "GET":
            resp.headers = {}
        return resp


@pytest.mark.asyncio
async def test_reconcile_fails_closed_without_exact_count(mirror_env):
    http = _NoCountHTTP()
    http.rows.append({"id": "r1", "workspace_id": "ws-test", "job_id": None,
                      "estimated_cents": 1, "actual_cents": None,
                      "created_at": "2026-11-10T00:00:00Z"})
    rec = await usage_ledger.reconcile_mirror(http=http)
    assert rec["ok"] is False and rec["error"] == "mirror_count_unknown"


@pytest.mark.asyncio
async def test_reconcile_preserves_active_holds(mirror_env, redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100000")
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    estimated_cents=70, job_id="j1")
    held = await usage_ledger.check_and_hold(job_id="j2", estimated_cents=500)
    assert held["ok"] is True
    rec = await usage_ledger.reconcile_mirror(http=mirror_env)
    assert rec["ok"] is True and rec["holds_preserved"] >= 1
    totals = await redis_fake.hgetall(usage_ledger._totals_key("ws-test"))
    spent = sum(int(v) for k, v in totals.items() if not k.startswith("held:"))
    held_sum = sum(int(v) for k, v in totals.items() if k.startswith("held:"))
    assert 70 <= spent
    assert held_sum >= 500


@pytest.mark.asyncio
async def test_check_and_hold_fails_closed_during_rebuild(mirror_env, redis_fake):
    await runtime_settings.set_value("USAGE_CAP_DAILY_CENTS", "100000")
    await redis_fake.set(usage_ledger._rebuild_lock_key("ws-test"), "1")
    res = await usage_ledger.check_and_hold(job_id="j9", estimated_cents=10)
    assert res["ok"] is False and res["error"] == "ledger_rebuild_in_progress"
    # negative control: without the lock the same hold is admitted
    await redis_fake.delete(usage_ledger._rebuild_lock_key("ws-test"))
    ok = await usage_ledger.check_and_hold(job_id="j9", estimated_cents=10)
    assert ok["ok"] is True


@pytest.mark.asyncio
async def test_reconcile_lock_released_after_run(mirror_env):
    rec = await usage_ledger.reconcile_mirror(http=mirror_env)
    assert rec["ok"] is True
    client = usage_ledger.redis.from_url("redis://fake")
    assert await client.get(usage_ledger._rebuild_lock_key("ws-test")) is None
