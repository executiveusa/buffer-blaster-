"""Authenticated no-spend REST surface for canonical UGC plan receipts."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.media_contracts import UGCPlanDraft
from ..services.media_receipts import create_ugc_plan, get_ugc_plan

router = APIRouter(prefix="/api/studio/ugc", tags=["ugc-receipts"])


@router.post("/plans")
async def create_plan(request: UGCPlanDraft, _=Depends(verify_operator)) -> dict:
    return await create_ugc_plan(request)


@router.get("/plans/{plan_id}")
async def read_plan(plan_id: str, _=Depends(verify_operator)) -> dict:
    return await get_ugc_plan(plan_id)
