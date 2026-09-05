"""Authenticated no-spend provider capability planning routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.provider_registry import ProviderRouteRequest, plan_provider_route, provider_registry


router = APIRouter(prefix="/api/studio/providers", tags=["provider-routing"])


@router.get("/capabilities")
async def capabilities(_=Depends(verify_operator)) -> dict:
    return {
        "ok": True,
        "providers": [entry.model_dump(mode="json") for entry in provider_registry()],
        "paid_generation": False,
    }


@router.post("/route")
async def dry_run_route(request: ProviderRouteRequest, _=Depends(verify_operator)) -> dict:
    return await plan_provider_route(request)
