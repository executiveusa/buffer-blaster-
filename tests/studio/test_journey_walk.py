"""Journey-truth walk: prove the A-to-Z UGC ad journey or name the exact break.

Stages mirror scripts/production/journey_walk.py. Only the paid/external
boundary is faked (provider, storage, ffmpeg, Redis store, durable ledger);
routing, auth, approval gates, wallet economics, and executor state machines
run for real.
"""
from __future__ import annotations

import os

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
def journey(monkeypatch, tmp_path):
    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    monkeypatch.delenv("INTERNAL_WALLET_PROVISIONING_ENABLED", raising=False)
    monkeypatch.setenv("FACTORY_WORK_ROOT", str(tmp_path))
    doubles = patch_journey_boundary()
    client = TestClient(app)
    auth = {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}
    return {"client": client, "auth": auth, "doubles": doubles}


def test_stage_01_health_is_public(journey):
    response = journey["client"].get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["approval_gate"] is True
    assert TEST_OPERATOR_KEY not in response.text


def test_stage_02_plan_is_free_and_operator_authenticated(journey):
    plan = journey["client"].post("/api/studio/ugc/factory/plan", json=BRIEF, headers=journey["auth"])
    assert plan.status_code == 200
    body = plan.json()
    assert body["ok"] is True
    assert body["gate"]["passed"] is True
    assert len(body["clips"]) == 2
    assert body["commercial"]["estimated_generation_cost_cents"] > 0
    denied = journey["client"].post("/api/studio/ugc/factory/plan", json=BRIEF)
    assert denied.status_code == 401


def test_stage_03_execute_without_approval_blocks(journey):
    response = journey["client"].post(
        "/api/studio/ugc/factory/execute",
        json={**BRIEF, "approved": False, "wallet_id": "anything", "idempotency_key": "walk-stage-03"},
        headers=journey["auth"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "human_approval_required"
    assert journey["doubles"]["provider"].calls == 0


def test_stage_04_execute_without_wallet_names_the_blocker(journey):
    response = journey["client"].post(
        "/api/studio/ugc/factory/execute",
        json={**BRIEF, "approved": True, "wallet_id": "missing-wallet", "idempotency_key": "walk-stage-04"},
        headers=journey["auth"],
    )
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "wallet_not_found"
    assert journey["doubles"]["provider"].calls == 0


def test_stage_05_internal_wallet_provisioning_is_off_by_default(journey):
    response = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "internal_ref": "team-seed-0001"},
        headers=journey["auth"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "internal_wallet_provisioning_disabled"
    denied = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "internal_ref": "team-seed-0001"},
    )
    assert denied.status_code == 401


def test_stage_06_internal_wallet_provisioning_when_enabled(journey, monkeypatch):
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    response = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "customer_ref": "internal-team", "internal_ref": "team-seed-0001"},
        headers=journey["auth"],
    )
    body = response.json()
    assert body["ok"] is True
    wallet = body["wallet"]
    assert wallet["state"] == "active"
    assert wallet["offer_id"] == "trial-7"
    assert wallet["remaining_ad_credits"] == 3
    assert wallet["remaining_provider_budget_cents"] == 400
    replay = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "customer_ref": "internal-team", "internal_ref": "team-seed-0001"},
        headers=journey["auth"],
    ).json()
    assert replay["ok"] is True
    assert replay["wallet"]["id"] == wallet["id"]
    assert replay.get("idempotent") is True


def test_stage_06b_internal_wallet_ref_conflict_is_truthful(journey, monkeypatch):
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    first = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "customer_ref": "internal-team", "internal_ref": "team-seed-0003"},
        headers=journey["auth"],
    ).json()
    assert first["ok"] is True

    different_offer = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-30", "customer_ref": "internal-team", "internal_ref": "team-seed-0003"},
        headers=journey["auth"],
    ).json()
    assert different_offer["ok"] is False
    assert different_offer["error"] == "session_ref_conflict"

    different_owner = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "customer_ref": "someone-else", "internal_ref": "team-seed-0003"},
        headers=journey["auth"],
    ).json()
    assert different_owner["ok"] is False
    assert different_owner["error"] == "session_ref_conflict"

    unchanged = journey["client"].get(
        f"/api/studio/billing/wallet/{first['wallet']['id']}", headers=journey["auth"]
    ).json()
    assert unchanged["wallet"]["offer_id"] == "trial-7"
    assert unchanged["wallet"]["remaining_ad_credits"] == 3


def test_stage_07_full_journey_finishes_a_video(journey, monkeypatch):
    monkeypatch.setenv("INTERNAL_WALLET_PROVISIONING_ENABLED", "true")
    wallet = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "internal_ref": "team-seed-0002"},
        headers=journey["auth"],
    ).json()["wallet"]

    plan = journey["client"].post("/api/studio/ugc/factory/plan", json=BRIEF, headers=journey["auth"]).json()
    assert plan["ok"] and plan["gate"]["passed"]

    executed = journey["client"].post(
        "/api/studio/ugc/factory/execute",
        json={**BRIEF, "approved": True, "wallet_id": wallet["id"], "idempotency_key": "walk-stage-07"},
        headers=journey["auth"],
    )
    body = executed.json()
    assert body["ok"] is True, body
    assert body["state"] == "finished"
    assert body["final_asset"]["signed_url"].endswith("final.mp4")
    assert body["qa"]["seam_passed"] is True
    assert body["allowance"]["remaining_provider_budget_after_cents"] == 100
    assert body["allowance"]["remaining_ad_credits_after"] == 0
    assert journey["doubles"]["provider"].calls >= 2
    states = [state for _, state in journey["doubles"]["ledger"].transitions]
    assert "rendering_clip_1" in states
    assert "stitching" in states
    assert states[-1] == "finished"

    after = journey["client"].get(f"/api/studio/billing/wallet/{wallet['id']}", headers=journey["auth"]).json()
    assert after["wallet"]["remaining_provider_budget_cents"] == 100
    assert after["wallet"]["remaining_ad_credits"] == 0

    exhausted = journey["client"].post(
        "/api/studio/ugc/factory/execute",
        json={**BRIEF, "approved": True, "wallet_id": wallet["id"], "idempotency_key": "walk-stage-07b"},
        headers=journey["auth"],
    ).json()
    assert exhausted["ok"] is False
    assert exhausted["error"] in {"provider_budget_exceeded", "ad_credits_exhausted"}
    assert TEST_OPERATOR_KEY not in executed.text


def test_stage_10_browser_path_stays_truthfully_blocked(journey):
    """The public browser journey is NOT repaired by this slice and must say so.

    Unauthenticated browser callers get a truthful 401 on planning, on
    execution, and on provisioning - never a fabricated success. Team browser
    bootstrap is out of scope for this slice and unresolved (docs/JOURNEY_WALK.md).
    """
    plan = journey["client"].post("/api/studio/ugc/factory/plan", json=BRIEF)
    assert plan.status_code == 401

    execute = journey["client"].post(
        "/api/studio/ugc/factory/execute",
        json={**BRIEF, "approved": True, "wallet_id": "anything", "idempotency_key": "walk-stage-10"},
    )
    assert execute.status_code == 401

    provision = journey["client"].post(
        "/api/studio/billing/internal-wallet",
        json={"offer_id": "trial-7", "internal_ref": "team-seed-0010"},
    )
    assert provision.status_code == 401

    status = journey["client"].get("/api/studio/status")
    assert status.status_code == 401
    assert journey["doubles"]["provider"].calls == 0
