"""Proof for the agent-wiring patch.

Only the paid/external boundary is faked (provider, storage, ffmpeg, Redis,
ledger). Routes, auth, scopes, approvals, wallet economics, refunds and the
executor state machine run for real.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary

BRIEF = {
    "product": "Cella Coffee",
    "audience": "home baristas",
    "pain": "getting inconsistent coffee every morning",
    "mechanism": "a measured roast and repeatable pour method",
    "offer": "POUR15",
}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    monkeypatch.setenv("FACTORY_WORK_ROOT", str(tmp_path))
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    doubles = patch_journey_boundary()
    client = TestClient(app)
    human = {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}
    return {"client": client, "human": human, "d": doubles}


def _wallet(env, ref: str) -> dict:
    body = env["client"].post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "internal_ref": ref}, headers=env["human"]).json()
    assert body["ok"], body
    return body["wallet"]


def _balance(env, wallet_id: str) -> tuple[int, int]:
    w = env["client"].get(f"/api/studio/billing/wallet/{wallet_id}", headers=env["human"]).json()["wallet"]
    return w["remaining_provider_budget_cents"], w["remaining_ad_credits"]


def _execute(env, wallet_id: str, key: str, headers=None, **extra) -> dict:
    payload = {**BRIEF, "wallet_id": wallet_id, "idempotency_key": key, **extra}
    if "approval_id" not in extra:
        payload.setdefault("approved", True)
    return env["client"].post("/api/studio/ugc/factory/execute", json=payload, headers=headers or env["human"]).json()


def _mcp(env, headers, name, arguments=None, method="tools/call"):
    params = {"name": name, "arguments": arguments or {}} if method == "tools/call" else {}
    resp = env["client"].post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, headers=headers)
    return resp


def _tool(env, headers, name, arguments=None) -> dict:
    resp = _mcp(env, headers, name, arguments)
    assert resp.status_code == 200, resp.text
    return resp.json()["result"]["structuredContent"]


def _agent(env, scopes, name="test-agent") -> dict:
    created = env["client"].post("/api/agent/tokens", json={"name": name, "scopes": scopes, "ttl_days": 7}, headers=env["human"]).json()
    assert created["ok"], created
    return {"Authorization": f"Bearer {created['token']}", "_id": created["token_id"]}


def _hdr(agent: dict) -> dict:
    return {"Authorization": agent["Authorization"]}


# ------------------------------------------------------------ refunds


def _break(env, monkeypatch, where: str):
    d = env["d"]
    if where == "clip_1":
        # Structured PRE-SEND refusal: the double carries the adapter's typed
        # charge_outcome, so settlement may treat it as definitely uncharged.
        async def bad_submit(**kwargs):
            d["provider"].calls += 1
            return {"ok": False, "error": "provider_rejected_before_send", "charge_outcome": "not_sent"}
        monkeypatch.setattr(d["provider"], "submit_video", bad_submit)
    elif where == "clip_2":
        original = d["provider"].submit_video

        async def second_fails(**kwargs):
            if d["provider"].calls >= 1:
                d["provider"].calls += 1
                return {"ok": False, "error": "provider_rejected_before_send", "charge_outcome": "not_sent"}
            return await original(**kwargs)
        monkeypatch.setattr(d["provider"], "submit_video", second_fails)
    elif where == "seed_upload":
        async def bad_upload(source, *, object_name, content_type, upsert=True):
            return {"ok": False, "error": "bucket_unreachable"}
        monkeypatch.setattr(d["storage"], "upload_file", bad_upload)
    elif where == "final_upload":
        original_upload = d["storage"].upload_file

        async def final_fails(source, *, object_name, content_type, upsert=True):
            if "/final-" in object_name and object_name.endswith(".mp4"):
                return {"ok": False, "error": "bucket_unreachable"}
            return await original_upload(source, object_name=object_name, content_type=content_type, upsert=upsert)
        monkeypatch.setattr(d["storage"], "upload_file", final_fails)
    elif where == "stitch":
        monkeypatch.setattr(d["media_ops"], "stitch", lambda a, b, c: {"ok": False, "error": "ffmpeg_failed"})
    elif where == "exception":
        def boom(a, b, c):
            raise RuntimeError("unexpected")
        monkeypatch.setattr(d["media_ops"], "stitch", boom)


# incurred_clips counts calls that REACHED the provider (accepted) plus
# uncertain after-send exceptions, each at its own input-shape estimate.
# Structured pre-send rejections are definitely not charged and settle at zero.
@pytest.mark.parametrize("where, incurred_clips", [
    ("clip_1", 0), ("clip_2", 1), ("seed_upload", 1), ("stitch", 2), ("final_upload", 2), ("exception", 2),
])
def test_every_failure_after_reservation_refunds_in_full_exactly_once(env, monkeypatch, where, incurred_clips):
    wallet = _wallet(env, f"refund-{where}-0001")
    before = _balance(env, wallet["id"])
    _break(env, monkeypatch, where)

    body = _execute(env, wallet["id"], f"refund-{where}-key")

    assert body["ok"] is False, body
    assert body["refunded"] is True, body
    assert body["release"]["idempotent_replay"] is False
    assert body["release"]["provider_cost_incurred_cents"] == incurred_clips * 80
    assert _balance(env, wallet["id"]) == before

    # Re-running the release is a replay and changes nothing.
    import asyncio
    from api.services.usage_wallet import release_reservation
    again = asyncio.run(release_reservation(wallet["id"], idempotency_key=f"refund-{where}-key", reason="retry"))
    assert again["ok"] and again["idempotent_replay"] is True
    assert _balance(env, wallet["id"]) == before


def test_success_is_not_refunded(env):
    wallet = _wallet(env, "success-0001")
    before = _balance(env, wallet["id"])
    body = _execute(env, wallet["id"], "success-key-1")
    assert body["ok"] is False and body["state"] == "needs_performance_review", body
    assert body["refunded"] is False and "release" not in body
    assert _balance(env, wallet["id"]) != before

    reviewed = env["client"].post("/api/studio/ugc/factory/review", json={
        "job_id": body["job_id"], "asset_sha256": body["final_asset_sha256"],
        "checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    }, headers=env["human"]).json()
    assert reviewed["ok"] is True and reviewed["state"] == "finished", reviewed


def test_release_without_reservation_and_reused_key(env):
    import asyncio
    from api.services.usage_wallet import release_reservation
    wallet = _wallet(env, "norelease-0001")
    missing = asyncio.run(release_reservation(wallet["id"], idempotency_key="never-reserved", reason="x"))
    assert missing == {"ok": False, "error": "reservation_not_found"}

    first = _execute(env, wallet["id"], "reuse-key-0001")
    assert first["ok"] is False and first["state"] == "needs_performance_review"
    replay = _execute(env, wallet["id"], "reuse-key-0001")
    assert replay["ok"] is False and replay["error"] == "idempotency_key_already_used"


# ------------------------------------------------------- price parity


def test_mcp_and_rest_reserve_what_the_executor_enforces(env, monkeypatch):
    # Plan-side env price differs from provider price: the old MCP path
    # reserved the plan price, then the executor rejected the reservation.
    monkeypatch.setenv("UGC_FACTORY_CLIP_COST_CENTS", "10")
    wallet = _wallet(env, "parity-0001")
    body = _tool(env, env["human"], "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "parity-key-1", "approved": True})
    assert body.get("error") != "invalid_spend_reservation", body
    assert body["ok"] is False and body["state"] == "needs_performance_review", body
    assert body["provider_pricing"]["estimated_clip_cost_cents"] == 80
    assert body["provider_pricing"]["clip_costs_cents"] == {"clip_1": 80, "clip_2": 80, "seam_retry": 80}


# ------------------------------------------------------ rate-limit IP


def test_forwarded_for_ignored_from_untrusted_peer(monkeypatch):
    from starlette.requests import Request
    from api.deps import _client_ip

    def req(peer, xff):
        return Request({"type": "http", "headers": [(b"x-forwarded-for", xff.encode())], "client": (peer, 1)})

    assert _client_ip(req("203.0.113.9", "1.2.3.4")) == "203.0.113.9"
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.2")
    assert _client_ip(req("10.0.0.2", "6.6.6.6, 198.51.100.7")) == "198.51.100.7"
    assert _client_ip(req("203.0.113.9", "6.6.6.6")) == "203.0.113.9"


# ---------------------------------------------- agent end-to-end (MCP)


def test_agent_full_render_journey_requires_human_approval(env):
    agent = _agent(env, ["read", "plan", "render"])
    a = _hdr(agent)
    wallet = _wallet(env, "agent-journey-0001")

    me = _tool(env, a, "whoami")
    assert me["agent"] is True and me["can_grant_approvals"] is False

    est = _tool(env, a, "estimate_ugc_ad_factory", BRIEF)
    assert est["ok"] and est["paid_generation"] is False
    cost = est["estimated_generation_cost_cents"]

    # Self-approval is impossible: approved=true from an agent is ignored.
    selfie = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "agent-key-0001", "approved": True})
    assert selfie["error"] == "human_approval_required"
    assert env["d"]["provider"].calls == 0

    req = _tool(env, a, "request_render_approval", {**BRIEF, "wallet_id": wallet["id"]})
    assert req["ok"] and req["status"] == "pending" and req["max_cost_cents"] == cost
    approval_id = req["approval_id"]

    pending = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "agent-key-0002", "approval_id": approval_id})
    assert pending["error"] == "approval_not_granted"

    # Agents cannot decide approvals.
    denied = env["client"].post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=a)
    assert denied.status_code == 403

    ok = env["client"].post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=env["human"]).json()
    assert ok == {"ok": True, "approval_id": approval_id, "status": "approved"}

    # Tampered brief is rejected and does not burn the approval.
    tampered = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "product": "Other", "wallet_id": wallet["id"], "idempotency_key": "agent-key-0003", "approval_id": approval_id})
    assert tampered["error"] == "approval_payload_mismatch"

    done = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "agent-key-0004", "approval_id": approval_id})
    # An agent-run render is never self-accepted: without a human performance
    # review attestation it stops at needs_performance_review. The final asset
    # is still delivered and stored, so the reservation is not refunded.
    assert done["ok"] is False and done["state"] == "needs_performance_review", done
    assert done["refunded"] is False and "release" not in done
    assert done["identity"] == f"agent:{agent['_id']}"

    # The human then reviews the actual rendered asset and finishes the job.
    reviewed = env["client"].post("/api/studio/ugc/factory/review", json={
        "job_id": done["job_id"], "asset_sha256": done["final_asset_sha256"],
        "checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    }, headers=env["human"]).json()
    assert reviewed["ok"] is True and reviewed["state"] == "finished", reviewed


    reuse = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "agent-key-0005", "approval_id": approval_id})
    assert reuse["error"] == "approval_already_used"

    status = _tool(env, a, "get_approval", {"approval_id": approval_id})
    assert status["approval"]["status"] == "consumed"


def test_review_route_maps_cas_conflict_to_409(env, monkeypatch):
    async def fake_conflict(job_id, review):
        return {"ok": False, "error": "performance_review_conflict", "detail": "job changed concurrently"}

    monkeypatch.setattr("api.routers.studio.record_performance_review", fake_conflict)
    resp = env["client"].post("/api/studio/ugc/factory/review", json={
        "job_id": "job-any", "asset_sha256": "0" * 64,
        "checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    }, headers=env["human"])
    assert resp.status_code == 409
    assert "concurrently" in resp.json()["detail"]


def test_agent_cannot_self_attest_performance_review(env):
    agent = _agent(env, ["read", "plan", "render"])
    a = _hdr(agent)

    body = env["client"].post("/api/studio/ugc/factory/review", json={
        "job_id": "job-any", "asset_sha256": "0" * 64,
        "checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    }, headers=a).json()
    assert body["ok"] is False
    assert body["error"] == "agent_performance_review_not_accepted"
    assert env["d"]["provider"].calls == 0


def test_agent_scopes_filter_tools_and_block_calls(env):
    reader = _hdr(_agent(env, ["read"], "reader"))
    names = {t["name"] for t in _mcp(env, reader, "", method="tools/list").json()["result"]["tools"]}
    assert "whoami" in names and "execute_ugc_ad_factory" not in names and "create_ugc_ad_factory_plan" not in names
    blocked = _tool(env, reader, "create_ugc_ad_factory_plan", BRIEF)
    assert blocked == {"ok": False, "error": "scope_required", "scope": "plan"}
    rest = env["client"].post("/api/studio/ugc/factory/plan", json=BRIEF, headers=reader)
    assert rest.status_code == 403


def test_agent_tokens_are_default_deny_on_money_and_admin_routes(env):
    agent = _agent(env, ["read", "plan", "render", "publish"], "full")
    a = _hdr(agent)
    for method, path, body in [
        ("post", "/api/studio/billing/internal-wallet", {"offer_id": "trial-7", "internal_ref": "agent-made-0001"}),
        ("post", "/api/agent/tokens", {"name": "escalate", "scopes": ["render"]}),
        ("get", "/api/agent/tokens", None),
        ("get", "/api/admin/settings", None),
        ("post", "/api/studio/money-loop/experiments", {"name": "x"}),
    ]:
        resp = getattr(env["client"], method)(path, headers=a, **({"json": body} if body else {}))
        assert resp.status_code in {401, 403}, (path, resp.status_code, resp.text)

    revoked = env["client"].delete(f"/api/agent/tokens/{agent['_id']}", headers=env["human"]).json()
    assert revoked["revoked"] is True
    assert _mcp(env, a, "whoami").status_code == 401
    assert env["client"].post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers={"Authorization": "Bearer bba_fake_token"}).status_code == 401


def test_agent_cannot_publish_without_human_approval(env):
    a = _hdr(_agent(env, ["read", "publish"], "publisher"))
    drop = {"id": "drop-1", "content": "New roast is live", "format": "post", "platforms": [{"platform": "instagram"}],
            "scheduled_at": "2026-12-01T10:00:00Z", "approved": True}
    blocked = _tool(env, a, "schedule_social_drop", drop)
    assert blocked["ok"] is False and blocked["error"] == "human_approval_required"
    rest = env["client"].post("/api/studio/social/schedule", json=drop, headers=a).json()
    assert rest["ok"] is False and rest["error"] == "human_approval_required"
    req = _tool(env, a, "request_publish_approval", drop)
    assert req["ok"] and req["status"] == "pending"
    still = _tool(env, a, "schedule_social_drop", {**drop, "approval_id": req["approval_id"]})
    assert still["error"] == "approval_not_granted"


# ------------------------------------------- mixed per-call pricing settlement


def _mixed_pricing_with_clip2_failure(env, monkeypatch):
    """Text calls price 30c, image-input calls 50c; clip 2's paid call fails."""
    provider = env["d"]["provider"]
    monkeypatch.setattr(provider, "estimate_clip_cost_cents",
                        lambda model_name=None, *, image_url=None: 50 if image_url else 30)
    calls = {"n": 0}
    real_submit = provider.submit_video

    async def fail_after_first(**kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            # Structured pre-send rejection (typed like the real adapter).
            return {"ok": False, "error": "provider_rejected_before_send", "charge_outcome": "not_sent"}
        return await real_submit(**kwargs)

    monkeypatch.setattr(provider, "submit_video", fail_after_first)


def test_mixed_pricing_partial_failure_settles_each_call_at_its_own_rate_rest(env, monkeypatch):
    _mixed_pricing_with_clip2_failure(env, monkeypatch)
    wallet = _wallet(env, "mixed-0001")
    body = _execute(env, wallet["id"], "mixed-key-0001")
    assert body["refunded"] is True, body
    # clip 1 (text, 30c) was accepted and settles at its own rate. clip 2's
    # structured pre-send rejection is definitely not charged: it is accounted
    # separately, never at a flat clip rate and never as exposure.
    assert body["release"]["provider_cost_incurred_cents"] == 30, body["release"]
    assert body["provider_cost_definite_cents"] == 30, body
    assert body["provider_cost_uncertain_estimated_exposure_cents"] == 0, body
    assert body["provider_calls_rejected"] == 1, body


def test_mixed_pricing_partial_failure_settles_each_call_at_its_own_rate_mcp(env, monkeypatch):
    _mixed_pricing_with_clip2_failure(env, monkeypatch)
    wallet = _wallet(env, "mixed-0002")
    body = _tool(env, env["human"], "execute_ugc_ad_factory",
                 {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "mixed-key-0002", "approved": True})
    assert body["refunded"] is True, body
    assert body["release"]["provider_cost_incurred_cents"] == 30, body["release"]
    assert body["provider_calls_rejected"] == 1, body


def test_mixed_pricing_usage_rows_carry_each_calls_own_estimate(env, monkeypatch):
    _mixed_pricing_with_clip2_failure(env, monkeypatch)
    from api.services import usage_ledger
    captured = []
    real_record = usage_ledger.record_usage

    async def capture(**kwargs):
        captured.append(kwargs)
        return await real_record(**kwargs)

    monkeypatch.setattr(usage_ledger, "record_usage", capture)
    wallet = _wallet(env, "mixed-0003")
    body = _execute(env, wallet["id"], "mixed-key-0003")
    # Only the accepted call becomes a usage row; the rejection is not a charge.
    estimates = sorted(row["estimated_cents"] for row in captured)
    assert estimates == [30], captured


def test_after_send_transport_exception_settles_as_estimated_exposure_never_zero(env, monkeypatch):
    """A timeout DURING/AFTER send leaves the charge unknown: the run must
    settle it conservatively at the call's estimate (labeled estimated
    exposure, not an actual charge), still refunding the customer in full."""
    provider = env["d"]["provider"]

    async def timeout_on_send(**kwargs):
        raise TimeoutError("read timeout after send")

    monkeypatch.setattr(provider, "submit_video", timeout_on_send)
    wallet = _wallet(env, "timeout-0001")
    body = _execute(env, wallet["id"], "timeout-key-0001")
    assert body["ok"] is False, body
    assert body["refunded"] is True, body  # customer full-refund policy holds
    # Flat fake provider: the one attempted clip call estimates at 80.
    assert body["release"]["provider_cost_incurred_cents"] == 80, body["release"]
    assert body["provider_cost_definite_cents"] == 0, body
    assert body["provider_cost_uncertain_estimated_exposure_cents"] == 80, body


# ------------------------------------------- canonical durability gates


def test_runner_blocks_before_reservation_when_ledger_not_durable(env, monkeypatch):
    """The canonical durability gate runs before any wallet reservation and
    before any provider call; the wallet is untouched."""
    import api.services.factory_runner as runner

    monkeypatch.setattr(
        runner, "canonical_write_preflight",
        lambda: {"ok": False, "error": "canonical_ledger_unavailable", "state": "ledger_blocked"},
    )
    wallet = _wallet(env, "ledger-blocked-0001")
    before = _balance(env, wallet["id"])
    body = _execute(env, wallet["id"], "ledger-blocked-key")
    assert body["ok"] is False, body
    assert body["state"] == "ledger_blocked"
    assert body["error"] == "canonical_ledger_unavailable"
    assert _balance(env, wallet["id"]) == before  # no reservation happened
    assert env["d"]["provider"].calls == 0  # no provider call


def test_runner_blocks_before_agent_approval_is_consumed_when_ledger_not_durable(env, monkeypatch):
    """An agent's approved render must NOT consume the human approval when the
    canonical ledger cannot persist: the approval stays pending for retry."""
    import api.services.factory_runner as runner

    agent = _agent(env, ["read", "plan", "render"])
    a = _hdr(agent)
    wallet = _wallet(env, "ledger-blocked-0002")
    requested = _tool(env, a, "request_render_approval", {**BRIEF, "wallet_id": wallet["id"]})
    assert requested["ok"] is True, requested
    approval_id = requested["approval_id"]
    decided = env["client"].post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=env["human"]).json()
    assert decided["ok"] is True, decided

    monkeypatch.setattr(
        runner, "canonical_write_preflight",
        lambda: {"ok": False, "error": "canonical_workspace_not_configured", "state": "ledger_blocked"},
    )
    body = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "ledger-blocked-agent", "approval_id": approval_id})
    assert body["ok"] is False, body
    assert body["state"] == "ledger_blocked"
    assert env["d"]["provider"].calls == 0

    # The approval was NOT consumed: it is still approved, and once durability
    # is restored the same approval_id still authorizes the run.
    status = _tool(env, a, "get_approval", {"approval_id": approval_id})
    assert status["approval"]["status"] == "approved", status
    monkeypatch.setattr(
        runner, "canonical_write_preflight",
        lambda: {"ok": True, "backend": {"backend": "in-memory-ledger-double", "persistent": True, "canonical": True}},
    )
    body2 = _tool(env, a, "execute_ugc_ad_factory", {**BRIEF, "wallet_id": wallet["id"], "idempotency_key": "ledger-restored-agent", "approval_id": approval_id})
    assert body2["state"] == "needs_performance_review", body2


def test_finalize_write_loss_fails_closed_refunds_and_preserves_exposure(env, monkeypatch):
    """Final update_job lost => delivered asset without durable review state.
    The run must fail closed honestly, refund the customer in full, and still
    record the real provider exposure."""
    d = env["d"]
    original_update = d["ledger"].update_job

    async def lose_final_write(job_id, **changes):
        if changes.get("state") == "needs_performance_review":
            return None
        return await original_update(job_id, **changes)

    # The executor resolved update_job at patch time, so intercept ITS binding.
    monkeypatch.setattr("api.services.ugc_executor.update_job", lose_final_write)
    wallet = _wallet(env, "finalize-loss-0001")
    before = _balance(env, wallet["id"])
    body = _execute(env, wallet["id"], "finalize-loss-key")
    assert body["ok"] is False, body
    assert body["state"] == "ledger_finalize_failed"
    assert body["error"] == "final_review_state_not_durable"
    assert body["customer_deliverable"] is False
    assert body["refunded"] is True, body  # customer full-refund policy holds
    assert body["release"]["provider_cost_incurred_cents"] == 160, body["release"]
    assert body["provider_cost_definite_cents"] == 160, body  # two accepted calls at 80
    assert body["provider_cost_uncertain_estimated_exposure_cents"] == 0, body
    assert _balance(env, wallet["id"]) == before  # customer made whole
    assert d["provider"].calls == 2  # both paid calls really happened


# ------------------------------------------- real preflight (env-based)


def test_canonical_write_preflight_fails_closed_without_workspace(monkeypatch):
    from api.services import studio_ledger

    monkeypatch.delenv("BUFFER_BLASTER_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    res = studio_ledger.canonical_write_preflight()
    assert res["ok"] is False
    assert res["error"] == "canonical_workspace_not_configured"
    assert res["state"] == "ledger_blocked"


def test_canonical_write_preflight_fails_without_any_backend(monkeypatch):
    from api.services import studio_ledger

    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    res = studio_ledger.canonical_write_preflight()
    assert res["ok"] is False
    assert res["error"] == "canonical_ledger_unavailable"


def test_canonical_write_preflight_ok_with_redis_backend(monkeypatch):
    from api.services import studio_ledger

    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    res = studio_ledger.canonical_write_preflight()
    assert res["ok"] is True
    assert res["backend"]["backend"] == "redis"


# ------------------------------------------- usage-settlement durability


def _durable_ledger_env(monkeypatch):
    """Real usage-ledger semantics on fakeredis with a job cap configured."""
    import fakeredis
    from api.services import model_settings, usage_ledger

    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(usage_ledger.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(model_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")

    async def cap_settings(key, default=""):
        return {"USAGE_CAP_JOB_CENTS": "100000"}.get(key, default)

    monkeypatch.setattr(usage_ledger.runtime_settings, "get_value", cap_settings)
    return usage_ledger, fake


def test_usage_ledger_write_failure_blocks_settlement_and_keeps_cap_hold(env, monkeypatch):
    """record_usage durability failure => settlement fails CLOSED: the cap hold
    stays pending (reconcilable) instead of being freed with exposure
    unrecorded, and the blocker is reported distinctly from the cost_unknown
    backlog."""
    import asyncio
    usage_ledger, fake = _durable_ledger_env(monkeypatch)

    async def write_fails(**kwargs):
        return {"ok": False, "error": "ledger_write_failed", "detail": "SyntheticFailure"}

    monkeypatch.setattr(usage_ledger, "record_usage", write_fails)
    releases = []
    real_release = usage_ledger.release_hold

    async def spy_release(hold, **kwargs):
        releases.append(hold)
        return await real_release(hold, **kwargs)

    monkeypatch.setattr(usage_ledger, "release_hold", spy_release)

    wallet = _wallet(env, "settle-block-0001")
    body = _execute(env, wallet["id"], "settle-block-key")
    assert body["state"] == "needs_performance_review", body  # the render itself is fine
    blocked = body["usage_settlement_blocked"]
    assert blocked["error"] == "usage_ledger_not_durable"
    assert blocked["unrecorded_calls"] == 2
    assert blocked["hold_released"] is False
    assert blocked["hold_id"]
    assert releases == [], "the cap hold must NOT be released while usage rows are not durable"
    # The real provider exposure is still honestly reported, never zeroed.
    assert body["provider_cost_definite_cents"] == 160, body
    holds = asyncio.run(fake.hgetall(usage_ledger._holds_key("ws-test")))
    assert len(holds) == 1  # still pending: reconcilable, cap not freed


def test_usage_settlement_releases_hold_when_ledger_durable(env, monkeypatch):
    """The durable path is unchanged: rows record, the hold settles exactly once."""
    import asyncio
    usage_ledger, fake = _durable_ledger_env(monkeypatch)
    releases = []
    real_release = usage_ledger.release_hold

    async def spy_release(hold, **kwargs):
        releases.append(hold)
        return await real_release(hold, **kwargs)

    monkeypatch.setattr(usage_ledger, "release_hold", spy_release)

    wallet = _wallet(env, "settle-ok-0001")
    body = _execute(env, wallet["id"], "settle-ok-key")
    assert body["state"] == "needs_performance_review", body
    assert "usage_settlement_blocked" not in body, body
    assert body.get("usage_events_recorded") == 2, body
    assert len(releases) == 1
    holds = asyncio.run(fake.hgetall(usage_ledger._holds_key("ws-test")))
    assert len(holds) == 0  # settled: nothing pending
