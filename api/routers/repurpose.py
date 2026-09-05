"""Authenticated no-spend long-form repurpose planning routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.repurpose import RepurposePlanRequest, create_repurpose_plan, get_repurpose_plan

router = APIRouter(prefix="/api/studio/repurpose", tags=["repurpose"])


@router.post("/plans")
async def create_plan(request: RepurposePlanRequest, _=Depends(verify_operator)) -> dict:
    return await create_repurpose_plan(request)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, _=Depends(verify_operator)) -> dict:
    return await get_repurpose_plan(plan_id)
