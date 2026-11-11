"""S4: spend ledger, caps before reservation, model/reasoning settings, usage API."""
from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services import model_settings, usage_ledger
from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary


@pytest.fixture
def redis_fake(monkeypatch):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(usage_ledger.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(model_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    return fake


@pytest.fixture
def env(monkeypatch, redis_fake):
    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    patch_journey_boundary()
    return TestClient(app), {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}


async def _set_cap(monkeypatch, key, value):
    async def fake_get(k, default=""):
        return value if k == key else default
    monkeypatch.setattr(usage_ledger.runtime_settings, "get_value", fake_get)


# ---------------------------------------------------------------- ledger


@pytest.mark.asyncio
async def test_record_usage_appends_one_row_per_call(redis_fake):
    r1 = await usage_ledger.record_usage(actor="user:u1", provider="fal", model="m1", kind="video",
                                         job_id="job-1", estimated_cents=80)
    r2 = await usage_ledger.record_usage(actor="user:u1", provider="openrouter", model="gpt-x", kind="llm",
                                         job_id="job-1", tokens_in=10, tokens_out=20, actual_cents=3)
    assert r1["ok"] and r2["ok"]
    events = await usage_ledger.list_events()
    assert len(events) == 2
    assert {e["kind"] for e in events} == {"video", "llm"}


@pytest.mark.asyncio
async def test_invalid_kind_and_missing_fields_rejected(redis_fake):
    bad = await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="hologram")
    assert bad == {"ok": False, "error": "invalid_kind", "allowed": ["image", "llm", "transcribe", "video", "vision"]}
    missing = await usage_ledger.record_usage(actor="", provider="p", model="m", kind="llm")
    assert missing["ok"] is False


@pytest.mark.asyncio
async def test_estimated_and_actual_are_never_mixed(redis_fake):
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="j", estimated_cents=100)  # no actual yet
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="j", estimated_cents=100, actual_cents=95)
    report = await usage_ledger.usage_report(group_by="job")
    row = report["rows"][0]
    assert row["estimated_cents"] == 200
    assert row["actual_cents"] == 95
    assert row["actual_reported_events"] == 1  # estimate never counted as actual


# ---------------------------------------------------------------- caps


@pytest.mark.asyncio
async def test_no_caps_configured_allows(redis_fake):
    result = await usage_ledger.check_caps(job_id="j", additional_estimated_cents=10_000)
    assert result == {"ok": True, "caps_configured": False}


@pytest.mark.asyncio
async def test_job_cap_blocks_before_reservation(redis_fake, monkeypatch):
    await _set_cap(monkeypatch, "USAGE_CAP_JOB_CENTS", "150")
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="j1", actual_cents=100)
    blocked = await usage_ledger.check_caps(job_id="j1", additional_estimated_cents=80)
    assert blocked["ok"] is False and blocked["error"] == "job_cap_exceeded"
    assert blocked["job_spent_cents"] == 100 and blocked["job_cap_cents"] == 150
    ok = await usage_ledger.check_caps(job_id="j1", additional_estimated_cents=50)
    assert ok["ok"] is True


@pytest.mark.asyncio
async def test_workspace_daily_cap_blocks_with_workspace_error(redis_fake, monkeypatch):
    await _set_cap(monkeypatch, "USAGE_CAP_DAILY_CENTS", "120")
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="other-job", estimated_cents=100)
    blocked = await usage_ledger.check_caps(job_id="new-job", additional_estimated_cents=30)
    assert blocked["ok"] is False
    assert blocked["error"] == "workspace_cap_exceeded" and blocked["window"] == "daily"


@pytest.mark.asyncio
async def test_workspace_monthly_cap_blocks_with_workspace_error(redis_fake, monkeypatch):
    await _set_cap(monkeypatch, "USAGE_CAP_MONTHLY_CENTS", "120")
    await usage_ledger.record_usage(actor="a", provider="p", model="m", kind="video",
                                    job_id="other", estimated_cents=100)
    blocked = await usage_ledger.check_caps(job_id="new", additional_estimated_cents=30)
    assert blocked["ok"] is False
    assert blocked["error"] == "workspace_cap_exceeded" and blocked["window"] == "monthly"


def test_factory_run_blocked_by_cap_before_any_reservation(env, monkeypatch):
    client, headers = env
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    wallet = client.post("/api/studio/billing/internal-wallet",
                         json={"offer_id": "trial-7", "customer_ref": "internal-team", "internal_ref": "team-seed-cap"},
                         headers=headers).json()["wallet"]
    brief = {"product": "Beans", "audience": "Moms", "pain": "Tired", "mechanism": "Energy",
             "wallet_id": wallet["id"], "idempotency_key": "cap-test-1", "approved": True}
    import asyncio

    async def tiny_cap(k, default=""):
        return "1" if k == "USAGE_CAP_JOB_CENTS" else default
    monkeypatch.setattr(usage_ledger.runtime_settings, "get_value", tiny_cap)
    res = client.post("/api/studio/ugc/factory/execute", json=brief, headers=headers)
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is False and payload["error"] == "job_cap_exceeded"
    assert payload["state"] == "spend_blocked"
    after = client.post("/api/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": "get_usage_wallet", "arguments": {"wallet_id": wallet["id"]}}})
    import json as _json
    wallet_after = _json.loads(after.json()["result"]["content"][0]["text"])["wallet"]
    assert wallet_after["remaining_ad_credits"] == 3  # nothing was reserved


# ---------------------------------------------------------------- report + API


@pytest.mark.asyncio
async def test_group_by_variants_and_invalid(redis_fake):
    await usage_ledger.record_usage(actor="agent:bot", provider="p", model="m1", kind="llm",
                                    job_id="j1", tokens_in=5, tokens_out=7, actual_cents=2)
    for group_by in ("day", "model", "job", "agent"):
        report = await usage_ledger.usage_report(group_by=group_by)
        assert report["ok"] and len(report["rows"]) == 1
    assert (await usage_ledger.usage_report(group_by="model"))["rows"][0]["group"] == "m1"
    assert (await usage_ledger.usage_report(group_by="agent"))["rows"][0]["group"] == "agent:bot"
    bad = await usage_ledger.usage_report(group_by="hour")
    assert bad["ok"] is False and bad["error"] == "invalid_group_by"


def test_usage_api_json_and_csv_roundtrip(env):
    client, headers = env
    import asyncio
    asyncio.run(usage_ledger.record_usage(actor="user:u", provider="p", model="mx", kind="video",
                                          job_id="j", estimated_cents=80, actual_cents=79))
    as_json = client.get("/api/studio/usage?group_by=model", headers=headers)
    assert as_json.status_code == 200
    rows = as_json.json()["rows"]
    assert rows[0]["group"] == "mx" and rows[0]["actual_cents"] == 79
    as_csv = client.get("/api/studio/usage?group_by=model&format=csv", headers=headers)
    assert as_csv.status_code == 200 and as_csv.headers["content-type"].startswith("text/csv")
    import csv as _csv
    import io
    parsed = list(_csv.DictReader(io.StringIO(as_csv.text)))
    assert parsed[0]["group"] == "mx" and int(parsed[0]["actual_cents"]) == 79


def test_usage_api_requires_auth(env):
    client, _ = env
    assert client.get("/api/studio/usage").status_code in (401, 403)


def test_mcp_get_usage_summary(env):
    client, headers = env
    rpc = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
           "params": {"name": "get_usage_summary", "arguments": {"group_by": "day"}}}
    res = client.post("/api/mcp", json=rpc, headers=headers)
    assert res.status_code == 200
    import json as _json
    data = _json.loads(res.json()["result"]["content"][0]["text"])
    assert data["ok"] is True and data["group_by"] == "day"


# ---------------------------------------------------------------- model/reasoning settings


@pytest.mark.asyncio
async def test_resolution_order_job_over_step_over_workspace_over_env(redis_fake, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "base-model")
    async def ws_cfg(key, default=""):
        return {"MODEL_PROVIDER": "openrouter", "MODEL_NAME": "ws-model",
                "MODEL_REASONING_LEVEL": "low"}.get(key, default)
    monkeypatch.setattr(model_settings.runtime_settings, "get_value", ws_cfg)
    await model_settings.set_step_config("research", provider="openai", model="step-model")
    step_only = await model_settings.resolve_model_config(step="research")
    assert step_only["provider"] == "openai" and step_only["model"] == "step-model"
    assert step_only["reasoning_level"] == "low"  # from workspace
    job = await model_settings.resolve_model_config(step="research",
                                                    job_override={"model": "job-model", "reasoning_level": "high"})
    assert job["model"] == "job-model" and job["reasoning_level"] == "high"
    assert job["reasoning_param"] == "reasoning_effort"


@pytest.mark.asyncio
async def test_unknown_provider_reasoning_rejected_not_guessed(redis_fake, monkeypatch):
    result = await model_settings.resolve_model_config(
        job_override={"provider": "mystery-ai", "reasoning_level": "high"})
    assert result["ok"] is False
    assert result["error"] == "unknown_provider_reasoning_param"


@pytest.mark.asyncio
async def test_invalid_reasoning_level_rejected(redis_fake):
    result = await model_settings.resolve_model_config(job_override={"reasoning_level": "galaxy"})
    assert result["ok"] is False and result["error"] == "invalid_reasoning_level"


def test_reasoning_request_body_matches_vendor_verified_shapes():
    assert model_settings.reasoning_request_body("openrouter", "high") == {"reasoning": {"effort": "high"}}
    assert model_settings.reasoning_request_body("openai", "low") == {"reasoning_effort": "low"}
    assert model_settings.reasoning_request_body("mystery", "low") is None
