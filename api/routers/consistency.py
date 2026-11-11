"""Characters, products and locations (identity sets) plus waste-guard checks. No spend."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..services.consistency import (
    compile_shot_prompt, create_identity, get_identity, list_identities, shot_preflight, update_identity,
)
from ..services.integration_auth import require_human_write, require_scope, verify_operator

router = APIRouter(prefix="/api/studio/identities", tags=["consistency"])


class IdentityCreate(BaseModel):
    kind: Literal["character", "product", "location"]
    name: str = Field(min_length=2, max_length=80)
    photos: list[str] = Field(min_length=1, max_length=12)
    sheet_url: str | None = None
    identity_block: str = Field(default="", max_length=2000)


class IdentityUpdate(BaseModel):
    add_photos: list[str] = Field(default_factory=list, max_length=12)
    remove_photos: list[str] = Field(default_factory=list, max_length=12)
    sheet_url: str | None = None
    identity_block: str | None = Field(default=None, max_length=2000)


class PromptRequest(BaseModel):
    identity_block: str = Field(max_length=2000)
    motion_block: str = Field(max_length=2000)
    references: int = Field(default=0, ge=0, le=9)


class PreflightRequest(BaseModel):
    shot: dict[str, Any]
    identity_id: str | None = None
    provider_caps: dict[str, Any] | None = None


@router.post("")
async def create(body: IdentityCreate, http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "plan")
    require_human_write(http, identity)
    return await create_identity(kind=body.kind, name=body.name, photos=body.photos, sheet_url=body.sheet_url,
                                 identity_block=body.identity_block, created_by=identity)


@router.get("")
async def index(http: Request, kind: str | None = None, _: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "read")
    return await list_identities(kind)


@router.get("/{identity_id}")
async def read(identity_id: str, http: Request, _: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "read")
    return await get_identity(identity_id)


@router.patch("/{identity_id}")
async def update(identity_id: str, body: IdentityUpdate, http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "plan")
    require_human_write(http, identity)
    return await update_identity(identity_id, add_photos=body.add_photos, remove_photos=body.remove_photos,
                                 sheet_url=body.sheet_url, identity_block=body.identity_block)


@router.post("/prompt")
async def prompt(body: PromptRequest, http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "plan")
    require_human_write(http, identity)
    return compile_shot_prompt(body.identity_block, body.motion_block, references=body.references)


@router.post("/preflight")
async def preflight(body: PreflightRequest, http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "plan")
    require_human_write(http, identity)
    ident = None
    if body.identity_id:
        found = await get_identity(body.identity_id)
        if not found.get("ok"):
            return {"ok": False, "blockers": ["selected character/product not found"], "warnings": [], "paid_generation": False}
        ident = found["identity"]
    return shot_preflight(body.shot, identity=ident, provider_caps=body.provider_caps)
