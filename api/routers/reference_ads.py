"""Authenticated no-spend reference-ad intelligence routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.reference_ad import ReferenceAdIntake, analyze_reference_ad, get_reference_strategy


router = APIRouter(prefix="/api/studio/reference-ads", tags=["reference-ads"])


@router.post("/analyze")
async def analyze_reference(request: ReferenceAdIntake, _=Depends(verify_operator)) -> dict:
    return await analyze_reference_ad(request)


@router.get("/strategy/{receipt_id}")
async def read_reference_strategy(receipt_id: str, _=Depends(verify_operator)) -> dict:
    return await get_reference_strategy(receipt_id)
