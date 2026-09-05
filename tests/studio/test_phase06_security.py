from pathlib import Path

import pytest
from pydantic import ValidationError

from api.routers.studio import UGCFactoryExecuteRequest

ROOT = Path(__file__).resolve().parents[2]


def _execute_payload(**changes):
    payload = {
        "product": "Proof Hoodie",
        "audience": "streetwear buyers",
        "pain": "generic creative",
        "mechanism": "proof-led creator demo",
        "wallet_id": "wallet-123",
        "idempotency_key": "paid-run-0001",
        "approved": True,
    }
    payload.update(changes)
    return payload


def test_paid_rest_execution_requires_idempotency_key():
    payload = _execute_payload()
    payload.pop("idempotency_key")
    with pytest.raises(ValidationError):
        UGCFactoryExecuteRequest(**payload)
    with pytest.raises(ValidationError):
        UGCFactoryExecuteRequest(**_execute_payload(idempotency_key="short"))


def test_paid_rest_execution_accepts_bounded_idempotency_key():
    request = UGCFactoryExecuteRequest(**_execute_payload())
    assert request.idempotency_key == "paid-run-0001"
    assert request.approved is True


def test_mcp_paid_execution_requires_same_idempotency_contract():
    source = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    assert '"idempotency_key"' in source
    assert '"wallet_id", "idempotency_key", "approved"' in source
    assert "idempotency_key=idempotency_key" in source
    assert "idempotency_key_required" in source


def test_wallet_reservation_is_atomic_replay_safe_and_workspace_owned():
    source = (ROOT / "api/services/usage_wallet.py").read_text(encoding="utf-8")
    assert "reservation_idempotency_conflict" in source
    assert "'REPLAY'" in source
    assert "reservation_key" in source
    assert '"workspace_id": _workspace_id()' in source
    assert "stored_workspace != current_workspace" in source
    assert "HINCRBY" in source


def test_studio_ledger_service_role_queries_are_workspace_scoped():
    source = (ROOT / "api/services/studio_ledger.py").read_text(encoding="utf-8")
    assert '"workspace_id": f"eq.{workspace_id}"' in source
    assert "_workspace_matches(record)" in source
    assert "workspace_id" in source
    # High-authority PostgREST calls must not be id-only reads or updates.
    assert 'params={"id": f"eq.{job_id}", "limit": "1"}' not in source
    assert 'params={"id": f"eq.{job_id}"}' not in source


def test_consequential_routes_remain_operator_authenticated():
    studio = (ROOT / "api/routers/studio.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    money = (ROOT / "api/routers/money_loop.py").read_text(encoding="utf-8")
    assert "Depends(verify_operator)" in studio
    assert "verify_operator(request)" in mcp
    assert "Depends(verify_operator)" in money
    assert "human_approval_required" in studio


def test_deprecated_paid_render_bypasses_stay_closed():
    source = (ROOT / "api/routers/studio.py").read_text(encoding="utf-8")
    assert '@router.post("/ugc/render")' in source
    assert '@router.post("/ugc/factory/render")' in source
    assert source.count('"error": "guarded_factory_required"') >= 2
