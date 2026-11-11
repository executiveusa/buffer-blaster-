"""Agent access: scoped tokens (human-managed) and human approvals for spend/publish."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..services.agent_access import (
    SCOPES, create_agent_token, decide_approval, get_approval, is_agent, list_agent_tokens,
    list_approvals, publish_payload, request_approval, revoke_agent_token,
)
from ..services.factory_runner import request_render_approval
from ..services.integration_auth import (request_role, request_scopes, require_approver_role, require_scope,
                                        verify_human_operator, verify_operator)

router = APIRouter(prefix="/api/agent", tags=["agent-access"])


class TokenCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    scopes: list[Literal["read", "plan", "render", "publish"]]
    ttl_days: int = Field(default=30, ge=1, le=365)


class ApprovalRequest(BaseModel):
    kind: Literal["render", "publish"]
    payload: dict[str, Any]
    wallet_id: str | None = None


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]


@router.get("/whoami")
async def whoami(http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    return {"ok": True, "identity": identity, "agent": is_agent(identity), "role": request_role(http),
            "scopes": sorted(request_scopes(http)),
            "can_grant_approvals": not is_agent(identity), "all_scopes": list(SCOPES)}


@router.post("/tokens")
async def create_token(body: TokenCreate, http: Request, identity: str = Depends(verify_human_operator)) -> dict[str, Any]:
    require_approver_role(http)
    return await create_agent_token(name=body.name, scopes=list(body.scopes), ttl_days=body.ttl_days, created_by=identity)


@router.get("/tokens")
async def tokens(http: Request, _: str = Depends(verify_human_operator)) -> dict[str, Any]:
    require_approver_role(http)
    return await list_agent_tokens()


@router.delete("/tokens/{token_id}")
async def revoke(token_id: str, http: Request, identity: str = Depends(verify_human_operator)) -> dict[str, Any]:
    require_approver_role(http)
    return await revoke_agent_token(token_id, revoked_by=identity)


@router.post("/approvals")
async def create_approval(body: ApprovalRequest, http: Request, identity: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, body.kind)
    if body.kind == "render":
        return await request_render_approval(body.payload, wallet_id=str(body.wallet_id or body.payload.get("wallet_id") or ""), requested_by=identity)
    return await request_approval(kind="publish", payload=publish_payload(body.payload), requested_by=identity,
                                  summary=f"Publish to {len(body.payload.get('platforms') or [])} platform(s)")


@router.get("/approvals")
async def approvals(http: Request, status: str | None = None, _: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "read")
    return await list_approvals(status)


@router.get("/approvals/{approval_id}")
async def approval(approval_id: str, http: Request, _: str = Depends(verify_operator)) -> dict[str, Any]:
    require_scope(http, "read")
    return await get_approval(approval_id)


@router.post("/approvals/{approval_id}/decision")
async def decide(approval_id: str, body: ApprovalDecision, http: Request, identity: str = Depends(verify_human_operator)) -> dict[str, Any]:
    require_approver_role(http)
    return await decide_approval(approval_id, decision=body.decision, decided_by=identity)
