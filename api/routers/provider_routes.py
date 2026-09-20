"""Authenticated no-spend provider capability planning routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.provider_registry import ProviderRouteRequest, plan_provider_route, provider_registry
from ..services.media_generation import get_media_provider


router = APIRouter(prefix="/api/studio/providers", tags=["provider-routing"])


@router.get("/capabilities")
async def capabilities(_=Depends(verify_operator)) -> dict:
    return {
        "ok": True,
        "providers": [entry.model_dump(mode="json") for entry in provider_registry()],
        "paid_generation": False,
    }


@router.get("/models")
async def models(_=Depends(verify_operator)) -> dict:
    provider = get_media_provider()
    items = provider.models() if hasattr(provider, "models") else []
    return {
        "ok": True,
        "provider": provider.status().get("provider"),
        "models": items,
        "paid_generation": False,
    }


@router.post("/route")
async def dry_run_route(request: ProviderRouteRequest, _=Depends(verify_operator)) -> dict:
    return await plan_provider_route(request)
