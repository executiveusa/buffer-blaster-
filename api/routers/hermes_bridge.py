"""Machine-readable Hermes <-> Buffer Blaster handoff contract."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.hermes_bridge import experiment_id_for, get_experiment, list_receipts, record_receipt
from ..services.integration_auth import verify_operator
from ..services.money_loop import create_experiment

router = APIRouter(prefix="/api/studio/hermes", tags=["hermes"])


class HermesHandoff(BaseModel):
    correlation_id: str = Field(min_length=8, max_length=200)
    opportunity_id: str = Field(min_length=1, max_length=200)
    prospect: dict[str, Any] = Field(default_factory=dict)
    constraint: str = ""
    proof_hypothesis: str
    primary_kpi: str
    pass_threshold: float
    baseline: float | None = None
    kill_threshold: float | None = None
    attribution_window_hours: int = Field(default=168, ge=1, le=2160)
    budget_ceiling_cents: int = Field(default=0, ge=0)


class HermesReceipt(BaseModel):
    correlation_id: str = Field(min_length=8, max_length=200)
    experiment_id: str | None = None
    stage: Literal[
        "SCAN",
        "QUALIFY",
        "MODEL",
        "PROVE",
        "JUDGE",
        "APPROVE",
        "TEST",
        "VERIFY",
        "CLOSE",
        "ITERATE",
        "KILL",
        "COMPOUND",
        "HOLD",
    ]
    status: Literal["pending", "pass", "fail", "blocked", "complete"]
    evidence: dict[str, Any] = Field(default_factory=dict)


@router.post("/handoff")
async def handoff(payload: HermesHandoff, _=Depends(verify_operator)) -> dict[str, Any]:
    experiment_id = experiment_id_for(payload.correlation_id)
    experiment = await get_experiment(experiment_id)
    idempotent = experiment is not None
    if experiment is None:
        created = await create_experiment({
            "id": experiment_id,
            "name": f"Hermes proof: {payload.opportunity_id}",
            "hypothesis": payload.proof_hypothesis,
            "primary_kpi": payload.primary_kpi,
            "baseline": payload.baseline,
            "pass_threshold": payload.pass_threshold,
            "kill_threshold": payload.kill_threshold,
            "attribution_window_hours": payload.attribution_window_hours,
            "budget_ceiling_cents": payload.budget_ceiling_cents,
        })
        if not created.get("ok"):
            return created
        experiment = created["experiment"]

    receipt = await record_receipt(
        experiment_id=experiment_id,
        correlation_id=payload.correlation_id,
        stage="MODEL",
        status="complete",
        evidence={
            "opportunity_id": payload.opportunity_id,
            "constraint": payload.constraint,
            "prospect": payload.prospect,
            "source": "hermes",
        },
    )
    if not receipt.get("ok"):
        return receipt
    return {
        "ok": True,
        "correlation_id": payload.correlation_id,
        "experiment_id": experiment_id,
        "experiment": experiment,
        "receipt": receipt.get("receipt"),
        "idempotent": idempotent and receipt.get("idempotent", False),
        "next_stage": "PROVE",
        "human_approval_required_before_spend": True,
    }


@router.post("/receipts")
async def receipt(payload: HermesReceipt, _=Depends(verify_operator)) -> dict[str, Any]:
    return await record_receipt(
        experiment_id=payload.experiment_id,
        correlation_id=payload.correlation_id,
        stage=payload.stage,
        status=payload.status,
        evidence=payload.evidence,
    )


@router.get("/experiments/{experiment_id}/receipts")
async def receipts(
    experiment_id: str,
    correlation_id: str | None = None,
    _=Depends(verify_operator),
) -> dict[str, Any]:
    return await list_receipts(experiment_id, correlation_id)


@router.get("/contract")
async def contract(_=Depends(verify_operator)) -> dict[str, Any]:
    return {
        "version": "hermes-buffer-blaster-v1",
        "transport": "authenticated_rest",
        "idempotency": "correlation_id deterministically owns experiment and stage receipt ids",
        "stages": {
            "hermes": ["SCAN", "QUALIFY", "MODEL", "CLOSE", "ITERATE", "KILL", "COMPOUND"],
            "buffer_blaster": ["PROVE", "JUDGE", "TEST", "VERIFY"],
            "human": ["APPROVE"],
        },
        "approval": {
            "real_spend": "explicit human approval + concrete budget ceiling required",
            "publish": "explicit human approval required",
        },
        "endpoints": {
            "handoff": "POST /api/studio/hermes/handoff",
            "receipt": "POST /api/studio/hermes/receipts",
            "receipt_readback": "GET /api/studio/hermes/experiments/{experiment_id}/receipts",
        },
    }
