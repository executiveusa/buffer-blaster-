"""Authentication router for live operator access.

The demo frontend is publicly viewable without this route. When the live backend
is enabled, ``DEMO_PASSWORD`` must be configured explicitly; the API never falls
back to a committed or well-known password.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..services.native import get_core
from ..deps import issue_session, rate_limit_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class PasswordPayload(BaseModel):
    password: str


@router.post("/verify")
async def verify(payload: PasswordPayload, request: Request, _=Depends(rate_limit_auth)):
    configured_password = os.getenv("DEMO_PASSWORD", "").strip()
    if not configured_password:
        raise HTTPException(status_code=503, detail="Operator authentication is not configured")
    if not get_core().sessions.verify_password(payload.password, configured_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = issue_session()
    return {"session_token": token, "expires_in": 86400}


@router.post("/logout")
async def logout(request: Request):
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        get_core().sessions.invalidate(header.split(" ", 1)[1])
    return {"status": "logged out"}
