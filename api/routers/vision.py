"""S6 vision routes. Analyze is a PAID provider call: execute role, S4 cap
hold before the call, priced-actual settle after. Read is cached-only."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services import vision
from ..services.integration_auth import require_execute_role, verify_operator

router = APIRouter(prefix="/api/studio/vision", tags=["studio"])


class AnalyzeBody(BaseModel):
    asset_id: str = Field(min_length=8, max_length=64)
    plan_id: str | None = Field(default=None, max_length=64)


@router.post("/analyze")
async def analyze(body: AnalyzeBody, request: Any,
                  identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_execute_role(request)
    return await vision.analyze_footage(asset_id=body.asset_id, plan_id=body.plan_id,
                                        actor=identity)


@router.get("/{asset_id}")
async def get_analysis(asset_id: str, _=Depends(verify_operator)) -> dict[str, Any]:
    return await vision.get_footage_analysis(asset_id=asset_id)
