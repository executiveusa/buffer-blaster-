"""Content router — approval queue per client; approve/reject endpoints.

Every content unit returned is tagged with its source `schema` so the isolation
contract can be verified: a unit under `schema_brand_a` must never appear in
brand B's queue.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_session
from ..services import demo

router = APIRouter(prefix="/api/admin/content", tags=["content"])


@router.get("/{client_slug}")
async def content_queue(client_slug: str, _=Depends(verify_session)) -> dict:
    schema = demo.schema_for(client_slug)
    if schema is None:
        raise HTTPException(status_code=404, detail="client not found")
    units = demo.content_for(client_slug)
    return {"client": client_slug, "schema": schema, "units": units}


@router.post("/{unit_id}/approve")
async def approve(unit_id: str, _=Depends(verify_session)) -> dict:
    ok = demo.approve(unit_id)
    if not ok:
        raise HTTPException(status_code=404, detail="content unit not found")
    return {"unit_id": unit_id, "status": "approved"}


@router.post("/{unit_id}/reject")
async def reject(unit_id: str, _=Depends(verify_session)) -> dict:
    ok = demo.reject(unit_id)
    if not ok:
        raise HTTPException(status_code=404, detail="content unit not found")
    return {"unit_id": unit_id, "status": "rejected"}
