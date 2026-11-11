"""Supabase Auth human identities: JWT validation, workspace roles, gates.

Offline human-auth coverage, not a live GoTrue or migration proof:
- locally signed HS256 test JWTs stand in for GoTrue access tokens
- the membership lookup is faked at the module boundary (network never runs)
- every other layer (routers, gates, role checks, sessions) runs for real
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

import api.services.supabase_auth as supabase_auth
import api.services.usage_wallet as wallet
from api.app import app
from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary

TEST_JWT_SECRET = "test-only-supabase-jwt-secret"
WORKSPACE = "00000000-0000-0000-0000-000000000001"
ISSUER = "https://supabase.test/auth/v1"

OWNER_ID = str(uuid.uuid4())
APPROVER_ID = str(uuid.uuid4())
OPERATOR_ID = str(uuid.uuid4())
VIEWER_ID = str(uuid.uuid4())
STRANGER_ID = str(uuid.uuid4())
ROLES_BY_USER = {OWNER_ID: "owner", APPROVER_ID: "approver", OPERATOR_ID: "operator", VIEWER_ID: "viewer"}

BRIEF = {
    "product": "Cella Coffee",
    "audience": "home baristas",
    "pain": "getting inconsistent coffee every morning",
    "mechanism": "a measured roast and repeatable pour method",
    "offer": "POUR15",
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_jwt(sub: str, *, secret: str = TEST_JWT_SECRET, aud="authenticated", exp: int | None = None,
             iss: str | None = None, alg: str = "HS256") -> str:
    header = {"alg": alg, "typ": "JWT"}
    payload = {"sub": sub, "aud": aud, "exp": exp or int(time.time()) + 3600,
               "iat": int(time.time()), "role": "authenticated"}
    if iss:
        payload["iss"] = iss
    h = _b64(json.dumps(header, separators=(",", ":")).encode())
    p = _b64(json.dumps(payload, separators=(",", ":")).encode())
    if alg == "none":
        return f"{h}.{p}."
    sig = _b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def bearer(sub: str, **kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {sign_jwt(sub, **kwargs)}"}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE)
    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    monkeypatch.delenv("SUPABASE_JWT_ISSUER", raising=False)

    async def fake_fetch(user_id: str, workspace_id: str):
        if workspace_id != WORKSPACE:
            return None
        return ROLES_BY_USER.get(user_id)

    monkeypatch.setattr(supabase_auth, "fetch_member_role", fake_fetch)
    patch_journey_boundary()
    return TestClient(app)


# ---------------------------------------------------------------- JWT validation


def test_valid_jwt_identity_and_role(env):
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["identity"] == f"user:{OWNER_ID}"
    assert body["role"] == "owner"
    assert body["agent"] is False


def test_expired_jwt_rejected(env):
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID, exp=int(time.time()) - 600))
    assert r.status_code == 401


def test_wrong_audience_rejected(env):
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID, aud="service_role"))
    assert r.status_code == 401


def test_wrong_signature_rejected(env):
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID, secret="some-other-secret"))
    assert r.status_code == 401


def test_alg_none_rejected(env):
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID, alg="none"))
    assert r.status_code == 401


def test_tampered_payload_rejected(env):
    token = sign_jwt(VIEWER_ID)
    h, _p, s = token.split(".")
    forged = f"{h}.{_b64(json.dumps({'sub': OWNER_ID, 'aud': 'authenticated', 'exp': int(time.time()) + 3600}).encode())}.{s}"
    r = env.get("/api/agent/whoami", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_non_member_rejected(env):
    r = env.get("/api/agent/whoami", headers=bearer(STRANGER_ID))
    assert r.status_code == 401


def test_foreign_workspace_rejected(env, monkeypatch):
    async def other_workspace(user_id, workspace_id):
        return None  # user is a member somewhere else, not here

    monkeypatch.setattr(supabase_auth, "fetch_member_role", other_workspace)
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID))
    assert r.status_code == 401


def test_unknown_db_role_rejected(env, monkeypatch):
    async def bogus_role(user_id, workspace_id):
        return "superadmin"

    monkeypatch.setattr(supabase_auth, "fetch_member_role", bogus_role)
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID))
    assert r.status_code == 401


def test_member_store_unreachable_fails_closed(env, monkeypatch):
    async def down(user_id, workspace_id):
        raise httpx.ConnectError("rest down")

    monkeypatch.setattr(supabase_auth, "fetch_member_role", down)
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID))
    assert r.status_code == 401


def test_jwt_disabled_without_secret(env, monkeypatch):
    monkeypatch.delenv("SUPABASE_JWT_SECRET")
    r = env.get("/api/agent/whoami", headers=bearer(OWNER_ID))
    assert r.status_code == 401


def test_issuer_enforced_when_configured(env, monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", ISSUER)
    assert env.get("/api/agent/whoami", headers=bearer(OWNER_ID, iss="https://evil.example/auth/v1")).status_code == 401
    assert env.get("/api/agent/whoami", headers=bearer(OWNER_ID, iss=ISSUER)).status_code == 200
    assert env.get("/api/agent/whoami", headers=bearer(OWNER_ID)).status_code == 401  # missing iss


# ---------------------------------------------------------------- role gates


def _create_publish_approval(env, headers) -> str:
    r = env.post("/api/agent/approvals", json={"kind": "publish", "payload": {"content": "x", "platforms": ["tiktok"]}},
                 headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"], body
    return body["approval_id"] if "approval_id" in body else body["approval"]["id"]


def test_viewer_cannot_decide_approval_approver_can(env):
    approval_id = _create_publish_approval(env, bearer(VIEWER_ID))  # requesting is not deciding
    r = env.post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=bearer(VIEWER_ID))
    assert r.status_code == 403, r.text
    r = env.post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=bearer(APPROVER_ID))
    assert r.status_code == 200, r.text
    detail = env.get(f"/api/agent/approvals/{approval_id}", headers=bearer(VIEWER_ID)).json()
    assert detail["approval"]["decided_by"] == f"user:{APPROVER_ID}"


def test_operator_cannot_decide_approval(env):
    approval_id = _create_publish_approval(env, bearer(OPERATOR_ID))
    r = env.post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"}, headers=bearer(OPERATOR_ID))
    assert r.status_code == 403


def test_two_humans_leave_distinct_decided_by(env):
    first = _create_publish_approval(env, bearer(OWNER_ID))
    second = _create_publish_approval(env, bearer(OWNER_ID))
    env.post(f"/api/agent/approvals/{first}/decision", json={"decision": "approved"}, headers=bearer(OWNER_ID))
    env.post(f"/api/agent/approvals/{second}/decision", json={"decision": "approved"}, headers=bearer(APPROVER_ID))
    one = env.get(f"/api/agent/approvals/{first}", headers=bearer(OWNER_ID)).json()["approval"]
    two = env.get(f"/api/agent/approvals/{second}", headers=bearer(OWNER_ID)).json()["approval"]
    assert one["decided_by"] == f"user:{OWNER_ID}"
    assert two["decided_by"] == f"user:{APPROVER_ID}"
    assert one["decided_by"] != two["decided_by"]


def test_token_management_requires_owner_or_approver(env):
    body = {"name": "ci-agent", "scopes": ["read", "plan"], "ttl_days": 7}
    for sub in (VIEWER_ID, OPERATOR_ID):
        assert env.post("/api/agent/tokens", json=body, headers=bearer(sub)).status_code == 403
        assert env.get("/api/agent/tokens", headers=bearer(sub)).status_code == 403
    created = env.post("/api/agent/tokens", json=body, headers=bearer(APPROVER_ID)).json()
    assert created["ok"], created
    listed = env.get("/api/agent/tokens", headers=bearer(OWNER_ID)).json()
    assert any(t["token_id"] == created["token_id"] for t in listed["tokens"])
    r = env.delete(f"/api/agent/tokens/{created['token_id']}", headers=bearer(VIEWER_ID))
    assert r.status_code == 403
    r = env.delete(f"/api/agent/tokens/{created['token_id']}", headers=bearer(OWNER_ID))
    assert r.status_code == 200, r.text


def test_viewer_cannot_execute_paid_factory_run(env):
    payload = {**BRIEF, "wallet_id": "missing-wallet", "idempotency_key": "viewer-exec-1", "approved": True}
    r = env.post("/api/studio/ugc/factory/execute", json=payload, headers=bearer(VIEWER_ID))
    assert r.status_code == 403, r.text
    # operator passes the role gate; the run then fails later on the unknown wallet
    r = env.post("/api/studio/ugc/factory/execute", json=payload, headers=bearer(OPERATOR_ID))
    assert r.status_code == 200, r.text
    assert r.json().get("error") == "wallet_not_found", r.json()


def test_viewer_cannot_publish_with_approved_flag(env):
    payload = {"id": "drop-1", "content": "hello", "format": "9:16",
               "platforms": [{"platform": "tiktok"}], "scheduled_at": "2030-01-01T00:00:00Z", "approved": True}
    r = env.post("/api/studio/social/schedule", json=payload, headers=bearer(VIEWER_ID))
    assert r.status_code == 403, r.text


def test_viewer_cannot_touch_money_loop(env):
    body = {"name": "exp", "hypothesis": "h", "primary_kpi": "ctr", "pass_threshold": 1.0}
    assert env.post("/api/studio/money-loop/experiments", json=body, headers=bearer(VIEWER_ID)).status_code == 403
    assert env.post("/api/studio/money-loop/experiments", json=body, headers=bearer(OPERATOR_ID)).status_code != 403


def test_agent_token_never_gets_human_role(env):
    created = env.post("/api/agent/tokens", json={"name": "bot", "scopes": ["read", "plan", "render"], "ttl_days": 7},
                       headers=bearer(OWNER_ID)).json()
    agent_headers = {"Authorization": f"Bearer {created['token']}"}
    who = env.get("/api/agent/whoami", headers=agent_headers).json()
    assert who["agent"] is True
    assert who["role"] is None
    assert env.post("/api/agent/tokens", json={"name": "bot2", "scopes": ["read"], "ttl_days": 7},
                    headers=agent_headers).status_code == 403
    approval_id = _create_publish_approval(env, bearer(OWNER_ID))
    assert env.post(f"/api/agent/approvals/{approval_id}/decision", json={"decision": "approved"},
                    headers=agent_headers).status_code == 403


# ---------------------------------------------------------------- legacy surfaces


def test_jwt_works_on_legacy_session_routes(env):
    r = env.get("/api/admin/dashboard", headers=bearer(VIEWER_ID))
    assert r.status_code == 200, r.text
    assert "Buffer Blaster" in r.json()["greeting"]


def test_viewer_read_only_on_legacy_admin_writes(env):
    r = env.post("/api/admin/clients", json={"name": "Acme", "niche": "food-beverage", "slug": "acme"}, headers=bearer(VIEWER_ID))
    assert r.status_code == 403, r.text
    r = env.post("/api/admin/clients", json={"name": "Acme", "niche": "food-beverage", "slug": "acme"}, headers=bearer(OPERATOR_ID))
    assert r.status_code != 403


def test_session_endpoint_reports_identity_and_role(env):
    r = env.get("/api/auth/session", headers=bearer(APPROVER_ID))
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "identity": f"user:{APPROVER_ID}", "role": "approver"}


def test_password_login_disabled_by_default(env, monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD_LOGIN_ENABLED", raising=False)
    r = env.post("/api/auth/verify", json={"password": "buffer-blaster-test-password"})
    assert r.status_code == 403


def test_password_login_behind_flag_still_works(env):
    r = env.post("/api/auth/verify", json={"password": "buffer-blaster-test-password"})
    assert r.status_code == 200, r.text  # conftest enables the flag for legacy tests
    token = r.json()["session_token"]
    r = env.get("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


def test_api_key_remains_break_glass_owner(env):
    headers = {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}
    who = env.get("/api/agent/whoami", headers=headers).json()
    assert who["identity"] == "api-key"
    assert who["role"] == "owner"
    assert env.post("/api/agent/tokens", json={"name": "kg", "scopes": ["read"], "ttl_days": 1}, headers=headers).status_code == 200


# ---------------------------------------------------------------- viewer read-only repair (reviewer pass 2)

import io

import api.routers.assets as assets_router
import api.routers.consistency as consistency_router
import api.routers.hermes_bridge as hermes_router
import api.routers.media_receipts as media_receipts_router
import api.routers.mcp as mcp_router
import api.routers.reference_ads as reference_ads_router
import api.routers.repurpose as repurpose_router
import api.routers.shopify_context as shopify_router
import api.routers.studio as studio_router


class Spy:
    """Fails the test if the gated service/provider boundary is reached."""

    def __init__(self):
        self.calls = 0

    async def __call__(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("gated boundary was invoked before denial")


def _spy_on(monkeypatch, module, *names) -> list[Spy]:
    spies = []
    for name in names:
        spy = Spy()
        monkeypatch.setattr(module, name, spy)
        spies.append(spy)
    return spies


SHA = "a" * 64
UUID1 = str(uuid.uuid4())


def test_viewer_denied_studio_mutations_without_provider_or_db_call(env, monkeypatch):
    spies = _spy_on(monkeypatch, studio_router, "activate_checkout_session", "provision_internal_wallet", "create_campaign")
    assert env.post("/api/studio/billing/activate", json={"checkout_session_id": "cs_test_x"}, headers=bearer(VIEWER_ID)).status_code == 403
    assert env.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "internal_ref": "viewer-attempt-1"},
                    headers=bearer(VIEWER_ID)).status_code == 403
    assert env.post("/api/studio/campaigns/plan", json={"brand": "Cella", "objective": "sales"}, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def test_viewer_denied_identity_writes_and_checks_without_store_call(env, monkeypatch):
    spies = _spy_on(monkeypatch, consistency_router, "create_identity", "update_identity", "compile_shot_prompt", "shot_preflight", "get_identity")
    body = {"kind": "character", "name": "Rosa", "photos": ["https://x.test/1.jpg"]}
    assert env.post("/api/studio/identities", json=body, headers=bearer(VIEWER_ID)).status_code == 403
    assert env.patch(f"/api/studio/identities/{UUID1}", json={"add_photos": ["https://x.test/2.jpg"]}, headers=bearer(VIEWER_ID)).status_code == 403
    assert env.post("/api/studio/identities/prompt", json={"identity_block": "a chef", "motion_block": "slow pour"},
                    headers=bearer(VIEWER_ID)).status_code == 403
    assert env.post("/api/studio/identities/preflight", json={"shot": {"duration_seconds": 10}}, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def test_viewer_denied_reference_asset_writes(env, monkeypatch):
    spies = _spy_on(monkeypatch, assets_router, "create_url_reference", "create_uploaded_reference")
    assert env.post("/api/studio/references/url", json={"url": "https://x.test/a.jpg"}, headers=bearer(VIEWER_ID)).status_code == 403
    files = {"file": ("ref.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")}
    assert env.post("/api/studio/references/upload", files=files, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def test_viewer_denied_reference_ad_analysis_without_provider_call(env, monkeypatch):
    spies = _spy_on(monkeypatch, reference_ads_router, "analyze_reference_ad")
    body = {"source_uri": "https://x.test/ad.mp4", "source_sha256": SHA, "source_owner": "cella",
            "rights_state": "owned", "transcript": "buy the coffee", "product_source_refs": [UUID1],
            "client_product": "Cella Coffee", "target_audience": "home baristas", "idempotency_key": "viewer-ref-1"}
    assert env.post("/api/studio/reference-ads/analyze", json=body, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def test_viewer_denied_plan_and_context_creation_without_db_call(env, monkeypatch):
    spies = _spy_on(monkeypatch, repurpose_router, "create_repurpose_plan")
    spies += _spy_on(monkeypatch, media_receipts_router, "create_ugc_plan")
    spies += _spy_on(monkeypatch, shopify_router, "create_shopify_context")
    repurpose_body = {"source_asset_key": "k", "source_duration_seconds": 60,
                      "transcript": [{"start_seconds": 0, "end_seconds": 1, "text": "hi"}], "idempotency_key": "viewer-rep-1"}
    assert env.post("/api/studio/repurpose/plans", json=repurpose_body, headers=bearer(VIEWER_ID)).status_code == 403
    plan_body = {"product_source_refs": [UUID1], "script": "hook line", "shot_plan": [{"shot": 1}],
                 "estimated_cost_ceiling_cents": 0, "idempotency_key": "viewer-plan-1"}
    assert env.post("/api/studio/ugc/plans", json=plan_body, headers=bearer(VIEWER_ID)).status_code == 403
    shopify_body = {"client_id": UUID1, "shop_domain": "cella.myshopify.com", "product_id": "1", "title": "Beans",
                    "idempotency_key": "viewer-shop-1"}
    assert env.post("/api/studio/shopify/context", json=shopify_body, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def test_viewer_denied_hermes_mutations_without_experiment_write(env, monkeypatch):
    spies = _spy_on(monkeypatch, hermes_router, "get_experiment", "create_experiment", "record_receipt")
    handoff = {"correlation_id": "corr-12345678", "opportunity_id": "opp-1", "proof_hypothesis": "h",
               "primary_kpi": "ctr", "pass_threshold": 1.0, "budget_ceiling_cents": 0}
    assert env.post("/api/studio/hermes/handoff", json=handoff, headers=bearer(VIEWER_ID)).status_code == 403
    receipt = {"correlation_id": "corr-12345678", "stage": "MODEL", "status": "complete"}
    assert env.post("/api/studio/hermes/receipts", json=receipt, headers=bearer(VIEWER_ID)).status_code == 403
    assert all(s.calls == 0 for s in spies)


def _mcp_call(env, name, arguments, headers):
    return env.post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                      "params": {"name": name, "arguments": arguments}}, headers=headers)


def test_viewer_denied_mcp_write_tools_without_side_effects(env, monkeypatch):
    spies = _spy_on(monkeypatch, mcp_router, "analyze_reference_ad", "create_identity", "create_ugc_plan", "request_approval")
    for tool, args in (
        ("analyze_reference_ad", {"source_uri": "https://x.test/ad.mp4", "source_sha256": SHA, "source_owner": "cella",
                                  "rights_state": "owned", "transcript": "t", "product_source_refs": [UUID1]}),
        ("create_identity", {"kind": "character", "name": "Rosa", "photos": ["https://x.test/1.jpg"]}),
        ("create_ugc_plan", {"product_source_refs": [UUID1], "script": "hook"}),
        ("request_publish_approval", {"content": "x", "platforms": [{"platform": "tiktok"}], "scheduled_at": "2030-01-01T00:00:00Z"}),
        ("compile_shot_prompt", {"identity_block": "chef", "motion_block": "pour"}),
        ("preflight_shot", {"shot": {"duration_seconds": 10}}),
        ("execute_ugc_ad_factory", {**BRIEF, "wallet_id": "w", "idempotency_key": "viewer-mcp-1", "approved": True}),
    ):
        r = _mcp_call(env, tool, args, bearer(VIEWER_ID))
        assert r.status_code == 200, (tool, r.text)
        result = r.json()["result"]
        assert result.get("isError") is True, (tool, result)
        assert result["structuredContent"]["error"] == "role_denied", (tool, result)
    assert all(s.calls == 0 for s in spies)


def test_viewer_mcp_reads_and_pure_tools_still_work(env):
    for tool, args in (
        ("list_identities", {}),
        ("whoami", {}),
        ("estimate_ugc_ad_factory", BRIEF),
        ("create_ugc_ad_factory_plan", BRIEF),
    ):
        r = _mcp_call(env, tool, args, bearer(VIEWER_ID))
        assert r.status_code == 200, (tool, r.text)
        result = r.json()["result"]
        assert not result.get("isError"), (tool, result)


async def _ok_stub(*args, **kwargs):
    return {"ok": True}


def test_operator_passes_new_write_gates(env, monkeypatch):
    # operator reaches the service boundary (gated function itself may fail later; not 403)
    spy = Spy.__new__(Spy)
    spy.calls = 0

    async def record(*args, **kwargs):
        spy.calls += 1
        return {"ok": True}

    monkeypatch.setattr(studio_router, "create_campaign", record)
    r = env.post("/api/studio/campaigns/plan", json={"brand": "Cella", "objective": "sales"}, headers=bearer(OPERATOR_ID))
    assert r.status_code != 403
    assert spy.calls == 1
    r = env.post("/api/studio/identities", json={"kind": "character", "name": "Rosa", "photos": ["https://x.test/1.jpg"]},
                 headers=bearer(OPERATOR_ID))
    assert r.status_code != 403


def test_agent_scope_path_unchanged_by_viewer_repair(env):
    # agents still authenticate via token + scope; the viewer repair adds no human bypass
    created = env.post("/api/agent/tokens", json={"name": "bot", "scopes": ["read", "plan"], "ttl_days": 7},
                       headers=bearer(OWNER_ID)).json()
    agent = {"Authorization": f"Bearer {created['token']}"}
    r = env.post("/api/studio/identities", json={"kind": "character", "name": "Rosa", "photos": ["https://x.test/1.jpg"]},
                 headers=agent)
    assert r.status_code == 200, r.text  # plan-scope write still works for agents
    r = _mcp_call(env, "create_identity", {"kind": "character", "name": "Rosa", "photos": ["https://x.test/1.jpg"]}, agent)
    assert r.status_code == 200 and not r.json()["result"].get("isError")
