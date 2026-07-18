"""Content router — approval queue per client; approve/reject endpoints.

Every content unit returned is tagged with its source `schema` so the isolation
contract can be verified: a unit under `schema_brand_a` must never appear in
brand B's queue.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..deps import verify_session
from ..db.repositories import content as content_repository

router = APIRouter(prefix="/api/admin/content", tags=["content"])


@router.get("/{client_slug}")
async def content_queue(client_slug: str, _=Depends(verify_session)) -> dict:
    result = content_repository.list_for_client(client_slug)
    if result is None:
        raise HTTPException(status_code=404, detail="client not found")
    schema, units = result
    return {"client": client_slug, "schema": schema, "units": units}


@router.post("/{unit_id}/approve")
async def approve(unit_id: str, _=Depends(verify_session)) -> dict:
    ok = content_repository.set_status(unit_id, "approved")
    if not ok:
        raise HTTPException(status_code=404, detail="content unit not found")
    return {"unit_id": unit_id, "status": "approved"}


@router.post("/{unit_id}/reject")
async def reject(unit_id: str, _=Depends(verify_session)) -> dict:
    ok = content_repository.set_status(unit_id, "rejected")
    if not ok:
        raise HTTPException(status_code=404, detail="content unit not found")
    return {"unit_id": unit_id, "status": "rejected"}
