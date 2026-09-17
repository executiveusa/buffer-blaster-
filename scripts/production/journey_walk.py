"""A-to-Z UGC operator journey walk against a live local server.

Proves the operator/agent journey brief -> plan -> approval -> video with the
paid/external boundary faked (no spend, no network to providers), or prints
the exact named break per stage. Exits 0 and prints JOURNEY_WALK_OK only when
every stage passes.

Run: python scripts/production/journey_walk.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BLASTER_API_KEY", "journey-walk-operator-key")
os.environ["FACTORY_WORK_ROOT"] = "/tmp/journey-walk-factory"

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary  # noqa: E402

PORT = 8137
BASE = f"http://127.0.0.1:{PORT}"
BRIEF = {
    "product": "Cella Coffee",
    "audience": "home baristas",
    "pain": "getting inconsistent coffee every morning",
    "mechanism": "a measured roast and repeatable pour method",
    "offer": "POUR15",
}

results: list[tuple[str, bool, str]] = []


def stage(name: str, passed: bool, detail: str) -> bool:
    results.append((name, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    return passed


def main() -> int:
    doubles = patch_journey_boundary()
    from api.app import app

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        print("FAIL: server did not start")
        return 1

    auth = {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}
    ok = True
    try:
        with httpx.Client(base_url=BASE, timeout=30) as http:
            health = http.get("/api/health")
            ok &= stage("01_health_public", health.status_code == 200 and health.json().get("approval_gate") is True, f"HTTP {health.status_code}")

            plan = http.post("/api/studio/ugc/factory/plan", json=BRIEF, headers=auth)
            plan_body = plan.json()
            ok &= stage("02_plan_free_operator_auth", plan.status_code == 200 and plan_body.get("ok") and plan_body.get("gate", {}).get("passed"), f"gate={plan_body.get('gate', {}).get('passed')}")

            unapproved = http.post("/api/studio/ugc/factory/execute", json={**BRIEF, "approved": False, "wallet_id": "x", "idempotency_key": "walk-stage-03"}, headers=auth).json()
            ok &= stage("03_execute_requires_approval", unapproved.get("error") == "human_approval_required", str(unapproved.get("error")))

            no_wallet = http.post("/api/studio/ugc/factory/execute", json={**BRIEF, "approved": True, "wallet_id": "missing", "idempotency_key": "walk-stage-04"}, headers=auth).json()
            ok &= stage("04_execute_requires_wallet", no_wallet.get("error") == "wallet_not_found", str(no_wallet.get("error")))

            os.environ.pop("INTERNAL_WALLET_PROVISIONING_ENABLED", None)
            disabled = http.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "internal_ref": "team-seed-0001"}, headers=auth).json()
            ok &= stage("05_internal_wallet_off_by_default", disabled.get("error") == "internal_wallet_provisioning_disabled", str(disabled.get("error")))

            os.environ["INTERNAL_WALLET_PROVISIONING_ENABLED"] = "true"
            provisioned = http.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "internal_ref": "team-seed-0002"}, headers=auth).json()
            wallet = provisioned.get("wallet") or {}
            ok &= stage("06_internal_wallet_provisions", provisioned.get("ok") is True and wallet.get("state") == "active", f"state={wallet.get('state')} credits={wallet.get('remaining_ad_credits')}")

            conflict_offer = http.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-30", "internal_ref": "team-seed-0002"}, headers=auth).json()
            conflict_owner = http.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "customer_ref": "someone-else", "internal_ref": "team-seed-0002"}, headers=auth).json()
            original = http.get(f"/api/studio/billing/wallet/{wallet.get('id', '')}", headers=auth).json().get("wallet") or {}
            conflict_ok = (
                conflict_offer.get("error") == "session_ref_conflict"
                and conflict_owner.get("error") == "session_ref_conflict"
                and original.get("offer_id") == "trial-7"
                and original.get("remaining_ad_credits") == 3
                and original.get("remaining_provider_budget_cents") == 400
            )
            ok &= stage("06b_wallet_ref_conflict_truthful", conflict_ok, f"offer={conflict_offer.get('error')} owner={conflict_owner.get('error')} wallet_unchanged={original.get('offer_id')}/{original.get('remaining_ad_credits')}/{original.get('remaining_provider_budget_cents')}")

            executed = http.post("/api/studio/ugc/factory/execute", json={**BRIEF, "approved": True, "wallet_id": wallet.get("id", ""), "idempotency_key": "walk-stage-07"}, headers=auth, timeout=60).json()
            ok &= stage("07_journey_finishes_video", executed.get("ok") is True and executed.get("state") == "finished", f"state={executed.get('state')} url={(executed.get('final_asset') or {}).get('signed_url')}")

            after = http.get(f"/api/studio/billing/wallet/{wallet.get('id', '')}", headers=auth).json().get("wallet") or {}
            ok &= stage("08_wallet_truth_after_spend", after.get("remaining_provider_budget_cents") == 100 and after.get("remaining_ad_credits") == 0, f"budget={after.get('remaining_provider_budget_cents')} credits={after.get('remaining_ad_credits')}")

        with httpx.Client(base_url=BASE, timeout=30) as anon:
            calls_before = doubles["provider"].calls
            anon_plan = anon.post("/api/studio/ugc/factory/plan", json=BRIEF)
            anon_exec = anon.post("/api/studio/ugc/factory/execute", json={**BRIEF, "approved": True, "wallet_id": "x", "idempotency_key": "walk-stage-10"})
            anon_prov = anon.post("/api/studio/billing/internal-wallet", json={"offer_id": "trial-7", "internal_ref": "team-seed-0010"})
            calls_after = doubles["provider"].calls
            browser_blocked = (
                anon_plan.status_code == 401
                and anon_exec.status_code == 401
                and anon_prov.status_code == 401
                and calls_after == calls_before
            )
            ok &= stage("10_browser_path_truthfully_blocked", browser_blocked, f"plan={anon_plan.status_code} execute={anon_exec.status_code} provision={anon_prov.status_code} provider_calls={calls_before}->{calls_after}")

        env = dict(os.environ, BLASTER_API_URL=BASE, BLASTER_API_KEY=TEST_OPERATOR_KEY)
        brief_file = Path("/tmp/journey-walk-brief.json")
        brief_file.write_text(json.dumps(BRIEF))
        provision_file = Path("/tmp/journey-walk-provision.json")
        provision_file.write_text(json.dumps({"offer_id": "trial-7", "customer_ref": "cli-walk", "internal_ref": "team-cli-walk-0901"}))
        cli_status = subprocess.run([sys.executable, "-m", "cli.blaster", "status"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        cli_plan = subprocess.run([sys.executable, "-m", "cli.blaster", "ugc-plan", str(brief_file)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        cli_provision = subprocess.run([sys.executable, "-m", "cli.blaster", "wallet-provision", str(provision_file)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        cli_wallet: subprocess.CompletedProcess | None = None
        cli_wallet_ok = False
        try:
            provision_body = json.loads(cli_provision.stdout)
            cli_wallet_id = str((provision_body.get("wallet") or {}).get("id") or "")
            provision_ok = (
                cli_provision.returncode == 0
                and provision_body.get("ok") is True
                and (provision_body.get("wallet") or {}).get("state") == "active"
                and (provision_body.get("wallet") or {}).get("remaining_ad_credits") == 3
                and (provision_body.get("wallet") or {}).get("remaining_provider_budget_cents") == 400
            )
            if cli_wallet_id:
                cli_wallet = subprocess.run([sys.executable, "-m", "cli.blaster", "wallet", cli_wallet_id], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
                wallet_body = json.loads(cli_wallet.stdout)
                cli_wallet_ok = (
                    cli_wallet.returncode == 0
                    and wallet_body.get("ok") is True
                    and (wallet_body.get("wallet") or {}).get("id") == cli_wallet_id
                    and (wallet_body.get("wallet") or {}).get("state") == "active"
                )
        except (json.JSONDecodeError, AttributeError):
            provision_ok = False
        cli_ok = (
            cli_status.returncode == 0
            and '"ok": true' in cli_status.stdout
            and cli_plan.returncode == 0
            and '"ok": true' in cli_plan.stdout
            and provision_ok
            and cli_wallet_ok
        )
        ok &= stage("09_cli_parity", cli_ok, f"status_rc={cli_status.returncode} plan_rc={cli_plan.returncode} provision_rc={cli_provision.returncode} provision_ok={provision_ok} wallet_readback_ok={cli_wallet_ok}")
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    failed = [name for name, passed, _ in results if not passed]
    if ok:
        print("JOURNEY_WALK_OK")
        return 0
    print(f"JOURNEY_WALK_FAILED: {', '.join(failed)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
