import pytest

from api.routers import hermes_bridge as router
from api.services.hermes_bridge import experiment_id_for, receipt_id_for


def test_hermes_ids_are_deterministic_and_stage_scoped():
    correlation = "opportunity-12345"
    assert experiment_id_for(correlation) == experiment_id_for(correlation)
    assert receipt_id_for(correlation, "MODEL") == receipt_id_for(correlation, "MODEL")
    assert receipt_id_for(correlation, "MODEL") != receipt_id_for(correlation, "VERIFY")
    assert experiment_id_for(correlation) != experiment_id_for("opportunity-54321")


@pytest.mark.asyncio
async def test_handoff_creates_one_deterministic_experiment_and_model_receipt(monkeypatch):
    captured = {}

    async def fake_get(_experiment_id):
        return None

    async def fake_create(payload):
        captured["experiment_payload"] = payload
        return {"ok": True, "experiment": {"id": payload["id"], "state": "draft"}}

    async def fake_receipt(**kwargs):
        captured["receipt"] = kwargs
        return {"ok": True, "receipt": {"stage": kwargs["stage"]}, "idempotent": False}

    monkeypatch.setattr(router, "get_experiment", fake_get)
    monkeypatch.setattr(router, "create_experiment", fake_create)
    monkeypatch.setattr(router, "record_receipt", fake_receipt)

    payload = router.HermesHandoff(
        correlation_id="hermes-opportunity-123",
        opportunity_id="opp-123",
        prospect={"company": "Example"},
        constraint="prove demand before scale",
        proof_hypothesis="The challenger increases qualified purchases",
        primary_kpi="net_roas",
        pass_threshold=2.0,
        budget_ceiling_cents=5000,
    )
    result = await router.handoff(payload, None)

    expected_id = experiment_id_for(payload.correlation_id)
    assert result["ok"] is True
    assert result["experiment_id"] == expected_id
    assert result["next_stage"] == "PROVE"
    assert result["human_approval_required_before_spend"] is True
    assert captured["experiment_payload"]["id"] == expected_id
    assert captured["experiment_payload"]["budget_ceiling_cents"] == 5000
    assert captured["receipt"]["stage"] == "MODEL"
    assert captured["receipt"]["status"] == "complete"
    assert captured["receipt"]["evidence"]["opportunity_id"] == "opp-123"


@pytest.mark.asyncio
async def test_handoff_retry_reuses_existing_experiment_and_receipt(monkeypatch):
    payload = router.HermesHandoff(
        correlation_id="hermes-opportunity-456",
        opportunity_id="opp-456",
        proof_hypothesis="A proof exists",
        primary_kpi="net_roas",
        pass_threshold=1.5,
    )
    expected_id = experiment_id_for(payload.correlation_id)

    async def fake_get(experiment_id):
        assert experiment_id == expected_id
        return {"id": expected_id, "state": "draft"}

    async def should_not_create(_payload):
        raise AssertionError("retry must not create a second experiment")

    async def fake_receipt(**_kwargs):
        return {"ok": True, "receipt": {"stage": "MODEL"}, "idempotent": True}

    monkeypatch.setattr(router, "get_experiment", fake_get)
    monkeypatch.setattr(router, "create_experiment", should_not_create)
    monkeypatch.setattr(router, "record_receipt", fake_receipt)

    result = await router.handoff(payload, None)
    assert result["ok"] is True
    assert result["experiment_id"] == expected_id
    assert result["idempotent"] is True


@pytest.mark.asyncio
async def test_contract_preserves_human_spend_and_publish_gate():
    result = await router.contract(None)
    assert result["approval"]["real_spend"] == "explicit human approval + concrete budget ceiling required"
    assert result["approval"]["publish"] == "explicit human approval required"
    assert result["transport"] == "authenticated_rest"
