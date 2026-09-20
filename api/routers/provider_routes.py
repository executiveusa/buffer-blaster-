"""Authenticated no-spend provider capability planning routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.provider_registry import ProviderRouteRequest, plan_provider_route, provider_registry
from ..services.media_generation import get_media_provider, media_providers


router = APIRouter(prefix="/api/studio/providers", tags=["provider-routing"])


@router.get("/capabilities")
async def capabilities(_=Depends(verify_operator)) -> dict:
    return {
        "ok": True,
        "providers": [entry.model_dump(mode="json") for entry in provider_registry()],
        "paid_generation": False,
    }


@router.get("/models")
async def models(provider: str | None = None, _=Depends(verify_operator)) -> dict:
    providers = media_providers()
    if provider:
        selected = providers.get(provider)
        if not selected:
            return {"ok": False, "error": "provider_not_configured", "provider": provider, "paid_generation": False}
        return {
            "ok": True,
            "provider": provider,
            "models": selected.models() if hasattr(selected, "models") else [],
            "paid_generation": False,
        }
    return {
        "ok": True,
        "providers": {
            name: (item.models() if hasattr(item, "models") else [])
            for name, item in sorted(providers.items())
        },
        "paid_generation": False,
    }


@router.post("/route")
async def dry_run_route(request: ProviderRouteRequest, _=Depends(verify_operator)) -> dict:
    return await plan_provider_route(request)
