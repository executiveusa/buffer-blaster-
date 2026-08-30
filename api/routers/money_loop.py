"""Operator-only API for proof-first experiment execution and measurement."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.integration_auth import verify_operator
from ..services.money_loop import (
    add_variant,
    create_experiment,
    evaluate,
    ingest_attribution_event,
    ingest_performance_event,
)

router = APIRouter(prefix="/api/studio/money-loop", tags=["money-loop"])


class ExperimentCreate(BaseModel):
    name: str
    hypothesis: str
    primary_kpi: str
    pass_threshold: float
    baseline: float | None = None
    kill_threshold: float | None = None
    campaign_id: str | None = None
    attribution_window_hours: int = Field(default=168, ge=1, le=2160)
    budget_ceiling_cents: int = Field(default=0, ge=0)


class VariantCreate(BaseModel):
    role: Literal["control", "variant"]
    label: str
    content_item_id: str | None = None
    hypothesis_delta: str = ""
    external_ad_refs: dict[str, Any] = Field(default_factory=dict)
    state: str = "draft"


class PerformanceEvent(BaseModel):
    content_item_id: str
    source: str
    metric: str
    value: float
    observed_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttributionEvent(BaseModel):
    source: str
    event_type: str
    experiment_id: str | None = None
    variant_id: str | None = None
    external_event_id: str | None = None
    revenue_cents: int | None = Field(default=None, ge=0)
    order_ref: str | None = None
    occurred_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantResultInput(BaseModel):
    variant_id: str
    role: Literal["control", "variant"]
    value: float
    spend_cents: int = Field(default=0, ge=0)
    sample_size: int = Field(default=0, ge=0)


class EvaluateRequest(BaseModel):
    variants: list[VariantResultInput]


@router.post("/experiments")
async def create(payload: ExperimentCreate, _=Depends(verify_operator)) -> dict[str, Any]:
    return await create_experiment(payload.model_dump())


@router.post("/experiments/{experiment_id}/variants")
async def variant(experiment_id: str, payload: VariantCreate, _=Depends(verify_operator)) -> dict[str, Any]:
    return await add_variant(experiment_id, payload.model_dump())


@router.post("/performance")
async def performance(payload: PerformanceEvent, _=Depends(verify_operator)) -> dict[str, Any]:
    return await ingest_performance_event(payload.model_dump())


@router.post("/attribution")
async def attribution(payload: AttributionEvent, _=Depends(verify_operator)) -> dict[str, Any]:
    return await ingest_attribution_event(payload.model_dump())


@router.post("/experiments/{experiment_id}/evaluate")
async def decide(experiment_id: str, payload: EvaluateRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    return await evaluate(experiment_id, [row.model_dump() for row in payload.variants])


@router.get("/contract")
async def contract(_=Depends(verify_operator)) -> dict[str, Any]:
    """Stable machine-readable handoff used by Hermes/Pauli orchestration."""
    return {
        "version": "money-loop-v1",
        "ownership": {
            "hermes": ["SCAN", "QUALIFY", "MODEL", "CLOSE", "COMPOUND"],
            "buffer_blaster": ["PROVE", "JUDGE", "TEST", "VERIFY", "SCALE"],
            "human_gate": ["APPROVE", "spend", "publish", "contractual_commitment"],
        },
        "input": {
            "opportunity_id": "string",
            "prospect": "object",
            "constraint": "string",
            "proof_hypothesis": "string",
            "primary_kpi": "string",
            "pass_threshold": "number",
            "budget_ceiling_cents": "integer",
        },
        "output": {
            "experiment_id": "string",
            "proof_asset_ids": "array[string]",
            "judge_receipts": "array[object]",
            "decision": "PASS|ITERATE|KILL|HOLD",
            "winner_variant_id": "string|null",
            "performance_evidence": "array[object]",
            "attribution_evidence": "array[object]",
        },
    }
