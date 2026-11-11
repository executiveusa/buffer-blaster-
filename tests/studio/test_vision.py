"""S6: agent vision - stubbed-transport proofs. NO actual paid calls.

Proves: schema validation (accept good, reject malformed incl. out-of-range
spans and bad confidence), retry-once-then-fail on malformed output with
EVERY call ledgered, cap denial before any provider call (spy), missing
pricing / per-frame-token config rejected pre-call, cache hit never
re-calls, cross-workspace invisibility, ffprobe fail-closed, duration and
frame-count bounds, plan linking.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import fakeredis
import pytest

from api.services import asset_storage, captions, runtime_settings, source_assets, usage_ledger, vision

GOOD = {
    "scenes": [{"start": 0, "end": 4, "summary": "person talks to camera"}],
    "hook_candidates": [{"start": 0, "end": 2, "why": "direct address"}],
    "product_visible": [{"start": 2, "end": 4, "confidence": 0.8}],
    "quality_flags": ["stable"],
    "suggested_cuts": [{"start": 3, "end": 4, "reason": "dead air"}],
}


@pytest.fixture
def env(monkeypatch, tmp_path):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(vision.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(captions.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(source_assets.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(usage_ledger.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(runtime_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("OPENROUTER_VISION_MODEL", "vendor/test-vl")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_PRICE_OPENROUTER_VENDOR_TEST_VL_IN_CENTS_PER_MTOK", "100")
    monkeypatch.setenv("LLM_PRICE_OPENROUTER_VENDOR_TEST_VL_OUT_CENTS_PER_MTOK", "300")
    monkeypatch.setenv("VISION_TOKENS_PER_FRAME_VENDOR_TEST_VL", "1000")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=6",
                    "-f", "lavfi", "-i", "sine=frequency=330:d=6",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(clip)],
                   capture_output=True, check=True, timeout=120)

    class FakeStorage:
        configured = True

        async def upload_file(self, source, *, object_name, content_type):
            return {"ok": True, "path": object_name, "signed_url": "https://signed.test/x"}

        async def download_url(self, url, dest):
            import shutil
            shutil.copy(clip, dest)
            return {"ok": True, "path": str(dest)}

        async def sign_path(self, path):
            return {"ok": True, "signed_url": "https://signed.test/x"}

    monkeypatch.setattr(asset_storage, "get_asset_storage", lambda: FakeStorage())
    monkeypatch.setattr(source_assets, "get_asset_storage", lambda: FakeStorage())
    return fake, clip


async def _register_asset(clip: Path, workspace: str = "ws-test") -> str:
    import os
    os.environ["BUFFER_BLASTER_WORKSPACE_ID"] = workspace
    rec = await source_assets.create_uploaded_reference(
        source=clip, filename="clip.mp4", content_type="video/mp4",
        metadata={"sha256": captions.sha256_file(clip)})
    assert rec.get("ok"), rec
    os.environ["BUFFER_BLASTER_WORKSPACE_ID"] = "ws-test"
    return rec["asset"]["id"]


def _transport(payload_obj=GOOD, tokens=(500, 120)):
    calls = {"n": 0, "payloads": []}

    async def t(payload, key):
        calls["n"] += 1
        calls["payloads"].append(payload)
        body = payload_obj if not callable(payload_obj) else payload_obj(calls["n"])
        return {"ok": True, "content": json.dumps(body) if not isinstance(body, str) else body,
                "tokens_in": tokens[0], "tokens_out": tokens[1], "actual_cents": None}

    return t, calls


# ------------------------------------------------------------ schema proof


def test_schema_accepts_valid_and_rejects_malformed():
    assert vision.validate_analysis(GOOD, 6.0)["ok"] is True
    bad_spans = dict(GOOD, scenes=[{"start": 5, "end": 99, "summary": "x"}])
    assert vision.validate_analysis(bad_spans, 6.0)["error"] == "malformed_model_output"
    bad_conf = dict(GOOD, product_visible=[{"start": 0, "end": 1, "confidence": 1.7}])
    assert vision.validate_analysis(bad_conf, 6.0)["ok"] is False
    missing = {k: v for k, v in GOOD.items() if k != "quality_flags"}
    assert vision.validate_analysis(missing, 6.0)["ok"] is False
    assert vision.validate_analysis("not a dict", 6.0)["ok"] is False
    assert vision.parse_model_json("```json\n" + json.dumps(GOOD) + "\n```") == GOOD
    assert vision.parse_model_json("no json here") is None


# ------------------------------------------------------------- happy path


@pytest.mark.asyncio
async def test_analyze_happy_path_ledgered_cached_and_plan_linked(env):
    fake, clip = env
    asset_id = await _register_asset(clip)
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, plan_id="plan-1",
                                       actor="user:u1", transport=t)
    assert res["ok"] is True and res["cache_hit"] is False
    assert res["frames_sampled"] == 3  # 6s clip at 1 frame / 2s
    assert res["analysis"]["scenes"][0]["summary"] == "person talks to camera"
    # image content actually sent
    imgs = [c for c in calls["payloads"][0]["messages"][1]["content"] if c["type"] == "image_url"]
    assert len(imgs) == 3 and imgs[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    # ledgered exactly once, kind=vision, priced actual from provider tokens
    events = await usage_ledger.list_events()
    assert len(events) == 1 and events[0]["kind"] == "vision"
    assert events[0]["tokens_in"] == 500 and events[0]["priced_actual_cents"] is not None
    assert events[0]["actual_cents"] is None  # provider-actuals only, never falsified
    # plan link + cache
    assert (await vision.get_footage_analysis(asset_id=asset_id))["ok"] is True
    again = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert again["cache_hit"] is True and calls["n"] == 1  # never re-called
    assert await fake.get(vision._plan_key("plan-1")) == res["sha256"]


@pytest.mark.asyncio
async def test_malformed_retries_once_then_fails_both_calls_ledgered(env):
    fake, clip = env
    asset_id = await _register_asset(clip)
    t, calls = _transport(payload_obj="this is not json")
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "malformed_model_output"
    assert calls["n"] == 2  # retried exactly once
    events = await usage_ledger.list_events()
    assert len(events) == 2 and all(e["kind"] == "vision" for e in events)
    assert (await vision.get_footage_analysis(asset_id=asset_id))["error"] == "not_analyzed"


@pytest.mark.asyncio
async def test_malformed_then_valid_succeeds_on_retry(env):
    fake, clip = env
    asset_id = await _register_asset(clip)
    t, calls = _transport(payload_obj=lambda n: "garbage" if n == 1 else GOOD)
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is True and calls["n"] == 2
    assert len(await usage_ledger.list_events()) == 2


@pytest.mark.asyncio
async def test_retry_uses_a_fresh_hold_per_attempt(env, monkeypatch):
    """F1: two paid calls need TWO reservations - a shared hold overshoots."""
    fake, clip = env
    await runtime_settings.set_value("USAGE_CAP_JOB_CENTS", "100000")  # real holds
    asset_id = await _register_asset(clip)
    holds_made = []
    real_hold = usage_ledger.check_and_hold

    async def spy_hold(**kw):
        res = await real_hold(**kw)
        if res.get("ok"):
            holds_made.append(res.get("hold"))
        return res

    monkeypatch.setattr(vision.usage_ledger, "check_and_hold", spy_hold)
    t, calls = _transport(payload_obj=lambda n: "garbage" if n == 1 else GOOD)
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is True and calls["n"] == 2
    assert len(holds_made) == 2 and holds_made[0]["hold_id"] != holds_made[1]["hold_id"]
    # both holds released after their call: nothing left held
    assert await fake.hgetall(usage_ledger._holds_key("ws-test")) == {}


@pytest.mark.asyncio
async def test_second_attempt_cap_denial_stops_before_second_paid_call(env, monkeypatch):
    """F1 negative control: if the retry's FRESH cap check denies, the second
    paid call never happens (one ledgered row, no overshoot)."""
    fake, clip = env
    asset_id = await _register_asset(clip)
    real_hold = usage_ledger.check_and_hold
    calls = {"holds": 0}

    async def deny_second(**kw):
        calls["holds"] += 1
        if calls["holds"] == 2:
            return {"ok": False, "error": "cap_exceeded", "window": "job"}
        return await real_hold(**kw)

    monkeypatch.setattr(vision.usage_ledger, "check_and_hold", deny_second)
    t, tcalls = _transport(payload_obj="garbage")  # would be malformed twice
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "usage_cap_exceeded" and res["attempt"] == 2
    assert tcalls["n"] == 1, "denied retry must not place the second paid call"
    assert len(await usage_ledger.list_events()) == 1


# ------------------------------------------------------- money boundaries


@pytest.mark.asyncio
async def test_cap_denial_means_no_provider_call(env, monkeypatch):
    fake, clip = env
    asset_id = await _register_asset(clip)
    await runtime_settings.set_value("USAGE_CAP_JOB_CENTS", "1")
    monkeypatch.setattr(vision, "MAX_TOKENS_OUT", 10_000)  # estimate 4c > 1c cap
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "usage_cap_exceeded"
    assert calls["n"] == 0, "cap denial must happen BEFORE any paid call"
    assert await usage_ledger.list_events() == []


@pytest.mark.asyncio
async def test_missing_pricing_rejected_before_provider_call(env, monkeypatch):
    fake, clip = env
    asset_id = await _register_asset(clip)
    monkeypatch.delenv("LLM_PRICE_OPENROUTER_VENDOR_TEST_VL_OUT_CENTS_PER_MTOK")
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "model_pricing_unconfigured"
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_missing_per_frame_tokens_rejected_before_provider_call(env, monkeypatch):
    fake, clip = env
    asset_id = await _register_asset(clip)
    monkeypatch.delenv("VISION_TOKENS_PER_FRAME_VENDOR_TEST_VL")
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "model_pricing_unconfigured"
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_provider_error_not_retried_blindly(env):
    fake, clip = env
    asset_id = await _register_asset(clip)
    calls = {"n": 0}

    async def boom(payload, key):
        calls["n"] += 1
        return {"ok": False, "error": "provider_error", "status": 500}

    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=boom)
    assert res["ok"] is False and res["error"] == "provider_error"
    assert calls["n"] == 1  # no blind double-spend
    # F2: the charged error exchange is ledgered CONSERVATIVELY (estimate
    # stands, actual unknown) - never an invisible refund
    events = await usage_ledger.list_events()
    assert len(events) == 1 and events[0]["kind"] == "vision"
    assert events[0]["estimated_cents"] is not None
    assert events[0]["actual_cents"] is None and events[0]["priced_actual_cents"] is None
    assert events[0]["cost_provenance"] == "reservation_estimate"


# --------------------------------------------------- bounds and isolation


@pytest.mark.asyncio
async def test_duration_over_cap_rejected(env, monkeypatch, tmp_path):
    fake, _ = env
    long_clip = tmp_path / "long.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64:d=8",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(long_clip)],
                   capture_output=True, check=True, timeout=120)
    monkeypatch.setattr(vision, "MAX_SECONDS", 5)
    asset_id = await _register_asset(long_clip)
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["error"] == "video_too_long" and calls["n"] == 0


@pytest.mark.asyncio
async def test_missing_ffprobe_fails_closed(env, monkeypatch):
    fake, clip = env
    asset_id = await _register_asset(clip)
    monkeypatch.setattr(vision.captions, "shutil_which", lambda b: False)
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["error"] == "ffprobe_unavailable" and calls["n"] == 0


@pytest.mark.asyncio
async def test_cross_workspace_asset_is_invisible(env):
    fake, clip = env
    asset_id = await _register_asset(clip, workspace="ws-other")
    t, calls = _transport()
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["error"] == "asset_not_found" and calls["n"] == 0
    assert (await vision.get_footage_analysis(asset_id=asset_id))["error"] == "asset_not_found"


def test_frame_bound_math():
    # 600s clip -> exactly MAX_FRAMES, never more (the 24-frame ceiling)
    assert min(vision.MAX_FRAMES, 600 // vision.FRAME_INTERVAL_S) == 24
    assert vision.MAX_FRAMES == 24 and vision.FRAME_INTERVAL_S == 2


@pytest.mark.asyncio
async def test_transport_raise_after_send_ledgers_conservative_cost(env):
    """Charged-timeout negative control: a post-send raise persists the
    reservation as a ledger row; the hold is then released (cost survives)."""
    fake, clip = env
    asset_id = await _register_asset(clip)

    async def timeout(payload, key):
        raise TimeoutError("read timed out after send")

    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=timeout)
    assert res["ok"] is False and res["error"] == "provider_transport_error"
    assert res["ledgered"] is True
    events = await usage_ledger.list_events()
    assert len(events) == 1 and events[0]["kind"] == "vision"
    assert events[0]["estimated_cents"] is not None
    assert events[0]["actual_cents"] is None
    assert events[0]["cost_provenance"] == "reservation_estimate"


@pytest.mark.asyncio
async def test_proven_unsent_transport_releases_with_zero_cost(env):
    """Only our own UnsentProven (connect never established) refunds."""

    async def refused(payload, key):
        raise vision.UnsentProven("connection refused before write")

    fake, clip = env
    asset_id = await _register_asset(clip)
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=refused)
    assert res["ok"] is False and res["error"] == "provider_transport_error"
    assert res["ledgered"] is False and res["unsent_proven"] is True
    assert await usage_ledger.list_events() == []
    assert await fake.hgetall(usage_ledger._holds_key("ws-test")) == {}


@pytest.mark.asyncio
async def test_arbitrary_exception_flag_is_not_unsent_proof(env):
    """Negative control: a vendor/SDK-style self-attestation flag takes the
    CONSERVATIVE path (ledgered), never the zero-cost path."""

    class VendorUnsentError(Exception):
        bb_unsent = True  # self-attestation is not proof

    async def attested(payload, key):
        raise VendorUnsentError("sdk claims nothing was sent")

    fake, clip = env
    asset_id = await _register_asset(clip)
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=attested)
    assert res["ok"] is False and res["error"] == "provider_transport_error"
    assert res["ledgered"] is True
    events = await usage_ledger.list_events()
    assert len(events) == 1 and events[0]["cost_provenance"] == "reservation_estimate"


@pytest.mark.asyncio
async def test_ledger_write_failure_keeps_hold_fail_closed(env, monkeypatch):
    """A paid call whose cost row cannot persist keeps its hold: the
    conservative reservation stays in cap totals (no invisible refund)."""
    fake, clip = env
    await runtime_settings.set_value("USAGE_CAP_JOB_CENTS", "100000")  # real hold exists
    asset_id = await _register_asset(clip)
    t, calls = _transport()

    async def broken_record_usage(**kw):
        return {"ok": False, "error": "ledger_store_unavailable"}

    monkeypatch.setattr(vision.usage_ledger, "record_usage", broken_record_usage)
    res = await vision.analyze_footage(asset_id=asset_id, actor="user:u1", transport=t)
    assert res["ok"] is False and res["error"] == "usage_ledger_write_failed"
    assert res["hold_kept"] is True and res["hold_id"], "operator hook: the kept hold's id"
    assert calls["n"] == 1
    holds = await fake.hgetall(usage_ledger._holds_key("ws-test"))
    assert len(holds) == 1, "hold must survive when the cost row cannot persist"
    assert res["hold_id"] in holds, "reported hold_id must resolve to the actual kept hold"
