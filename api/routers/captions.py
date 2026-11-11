"""S7 caption routes. Transcribe is zero-cost (self-hosted faster-whisper)
and cached by content hash; burn-in writes a NEW asset, original untouched.
Agents may call both (plan/write scope); no approval needed: no spend."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services import captions
from ..services.integration_auth import require_execute_role, verify_operator

router = APIRouter(prefix="/api/studio/captions", tags=["studio"])


class TranscribeBody(BaseModel):
    asset_id: str = Field(min_length=8, max_length=64)


class BurnBody(BaseModel):
    asset_id: str = Field(min_length=8, max_length=64)


@router.post("/transcribe")
async def transcribe(body: TranscribeBody, request: Any,
                     identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_execute_role(request)
    return await captions.transcribe_by_asset_id(asset_id=body.asset_id, actor=identity)


@router.post("/burn")
async def burn(body: BurnBody, request: Any,
               identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_execute_role(request)
    return await captions.burn_by_asset_id(asset_id=body.asset_id, actor=identity)


@router.get("/{asset_id}")
async def get_caption(asset_id: str, _=Depends(verify_operator)) -> dict[str, Any]:
    return await captions.get_captions(asset_id=asset_id)
