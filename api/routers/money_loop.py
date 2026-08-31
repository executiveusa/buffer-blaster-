"""Operator-only API for proof-first experiment execution and measurement."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.integration_auth import verify_operator
from ..services.money_loop import (
    add_variant,
    bind_variant_provider_ref,
    create_experiment,
    evaluate,
    ingest_attribution_event,
    ingest_performance_event,
)
from ..services.performance_ingestion import sync_experiment
from ..services.providers import get_ads_provider
from ..services.providers.registry import provider_statuses

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


class ProviderLaunch(BaseModel):
    variant_id: str
    approved: bool = False
    payload: dict[str, Any]


class ProviderRefAction(BaseModel):
    external_ref: dict[str, Any]
    approved: bool = False


class ProviderBind(BaseModel):
    variant_id: str
    external_ref: dict[str, Any]


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


@router.post("/experiments/{experiment_id}/sync")
async def sync(experiment_id: str, _=Depends(verify_operator)) -> dict[str, Any]:
    """Pull provider metrics, join Shopify attribution, then evaluate."""
    return await sync_experiment(experiment_id)


@router.get("/providers")
async def providers(_=Depends(verify_operator)) -> dict[str, Any]:
    return {"providers": provider_statuses()}


@router.post("/providers/{provider_name}/launch")
async def launch_provider(provider_name: str, payload: ProviderLaunch, _=Depends(verify_operator)) -> dict[str, Any]:
    try:
        provider = get_ads_provider(provider_name)
    except KeyError:
        return {"ok": False, "error": "unknown_ads_provider"}
    launched = await provider.create_experiment(payload.payload, approved=payload.approved)
    campaign_id = launched.get("campaign_id")
    if launched.get("ok") and campaign_id:
        bound = await bind_variant_provider_ref(payload.variant_id, provider_name, {"campaign_id": campaign_id})
        launched["variant_binding"] = bound
    return launched


@router.post("/providers/{provider_name}/bind")
async def bind_provider(provider_name: str, payload: ProviderBind, _=Depends(verify_operator)) -> dict[str, Any]:
    try:
        get_ads_provider(provider_name)
    except KeyError:
        return {"ok": False, "error": "unknown_ads_provider"}
    return await bind_variant_provider_ref(payload.variant_id, provider_name, payload.external_ref)


@router.post("/providers/{provider_name}/pause")
async def pause_provider(provider_name: str, payload: ProviderRefAction, _=Depends(verify_operator)) -> dict[str, Any]:
    try:
        provider = get_ads_provider(provider_name)
    except KeyError:
        return {"ok": False, "error": "unknown_ads_provider"}
    return await provider.pause_experiment(payload.external_ref, approved=payload.approved)


@router.post("/providers/{provider_name}/read")
async def read_provider(provider_name: str, payload: ProviderRefAction, _=Depends(verify_operator)) -> dict[str, Any]:
    try:
        provider = get_ads_provider(provider_name)
    except KeyError:
        return {"ok": False, "error": "unknown_ads_provider"}
    return await provider.read_experiment(payload.external_ref)


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
        "providers": {
            "paid_media": ["meta", "tiktok"],
            "revenue_truth": "shopify_webhooks",
            "shopify_endpoint": "/api/webhooks/shopify/orders",
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
