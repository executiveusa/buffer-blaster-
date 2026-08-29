"""Legacy admin pipeline simulation.

The production Social Studio execution path lives under `/api/studio/*`. This
legacy admin route is retained for demo compatibility and must report its
simulation state explicitly rather than claiming a Rust/Hermes production queue.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_session
from ..services import demo

router = APIRouter(prefix="/api/admin/pipeline", tags=["pipeline"])


@router.post("/{client_slug}/run")
async def run_pipeline(client_slug: str, _=Depends(verify_session)) -> dict:
    client = demo.get_client(client_slug)
    if not client:
        raise HTTPException(status_code=404, detail="client not found")
    run = demo.start_pipeline(client_slug)
    return {
        "status": "queued",
        "run_id": run["id"],
        "client": client_slug,
        "simulated": True,
        "canonical_production_path": "/api/studio/*",
    }


@router.get("/{client_slug}/status")
async def pipeline_status(client_slug: str, _=Depends(verify_session)) -> dict:
    return demo.pipeline_status(client_slug)


@router.post("/{client_slug}/cancel")
async def cancel_pipeline(client_slug: str, _=Depends(verify_session)) -> dict:
    run = demo.cancel_pipeline(client_slug)
    return {**run, "canonical_production_path": "/api/studio/*"}
