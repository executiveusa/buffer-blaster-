"""S5 footage connector routes. Tokens never appear in any response.

Connect/callback/revoke are human-only writes (agents get a consent URL via
MCP `connect_source` and a human completes the OAuth round-trip). Import is
an execute-role write, idempotent by key.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..services import footage, footage_import
from ..services.agent_access import is_agent
from ..services.integration_auth import (require_execute_role, require_human_write,
                                         verify_operator)


def _humans_connect_sources(identity: str) -> None:
    """Agents get a consent URL (MCP connect_source); the OAuth round-trip and
    any disconnect are human-only."""
    if is_agent(identity):
        raise HTTPException(status_code=403, detail="Source connections are completed by humans")

router = APIRouter(prefix="/api/studio/footage", tags=["studio"])


class CallbackBody(BaseModel):
    code: str = Field(min_length=4, max_length=2048)
    state: str = Field(min_length=8, max_length=128)


class ImportBody(BaseModel):
    provider: str = Field(pattern=r"^(google|onedrive|dropbox)$")
    filename: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    file_id: str | None = Field(default=None, max_length=255)
    link: str | None = Field(default=None, max_length=2048)


@router.get("/providers")
async def providers(_=Depends(verify_operator)) -> dict[str, Any]:
    return footage.provider_status()


@router.get("")
async def status(_=Depends(verify_operator)) -> dict[str, Any]:
    return await footage.connection_status()


@router.get("/connect/{provider}")
async def connect(provider: str, request: Request,
                  identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_execute_role(request)
    return await footage.consent_url(provider, actor=identity)


@router.post("/callback/{provider}")
async def callback(provider: str, body: CallbackBody, request: Request,
                   identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_human_write(request, identity)
    require_execute_role(request)
    _humans_connect_sources(identity)
    return await footage.complete_connect(provider, code=body.code, state=body.state,
                                          actor=identity)


@router.delete("/connections/{provider}")
async def disconnect(provider: str, request: Request,
                     identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_human_write(request, identity)
    require_execute_role(request)
    _humans_connect_sources(identity)
    return await footage.revoke(provider, actor=identity)


class PickedBody(BaseModel):
    file_ref: str = Field(min_length=1, max_length=2048)
    filename: str = Field(min_length=1, max_length=255)


@router.post("/picked/{provider}")
async def picked(provider: str, body: PickedBody, request: Request,
                 identity: str = Depends(verify_operator)) -> dict[str, Any]:
    """Register a human's picker selection (Google/OneDrive file_id, Dropbox
    chooser link). Only registered files can be imported - agents never
    browse or pick."""
    require_human_write(request, identity)
    _humans_connect_sources(identity)
    return await footage.register_picked_file(provider, file_ref=body.file_ref,
                                              filename=body.filename, actor=identity)


@router.delete("/picked/{provider}")
async def unpicked(provider: str, body: PickedBody, request: Request,
                   identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_human_write(request, identity)
    _humans_connect_sources(identity)
    return await footage.unpick_file(provider, file_ref=body.file_ref)


@router.get("/{provider}/files")
async def files(provider: str, limit: int = 50,
                _=Depends(verify_operator)) -> dict[str, Any]:
    """Only human picker-consented files - never a whole-drive listing."""
    return await footage.list_files(provider, limit=limit)


@router.post("/import")
async def import_route(body: ImportBody, request: Request,
                       identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_execute_role(request)
    return await footage_import.import_footage(
        provider=body.provider, actor=identity, filename=body.filename,
        idempotency_key=body.idempotency_key, file_id=body.file_id, link=body.link)
