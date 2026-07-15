"""Auth router — password-gated demo access.

`POST /api/auth/verify` checks the password against `DEMO_PASSWORD` (default
BLASTER2026), rate-limited to 5 attempts/min/IP. On success it mints a 256-bit
session token. The password is never logged.

Password comparison is constant-time via the core's `SessionStore.verify_password`
(`hmac.compare_digest` in the Python backend; `subtle::ConstantTimeEq` in Rust).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..services.native import get_core
from ..deps import issue_session, rate_limit_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

_DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "BLASTER2026")


class PasswordPayload(BaseModel):
    password: str


@router.post("/verify")
async def verify(payload: PasswordPayload, request: Request, _=Depends(rate_limit_auth)):
    if not get_core().sessions.verify_password(payload.password, _DEMO_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = issue_session()
    return {"session_token": token, "expires_in": 86400}


@router.post("/logout")
async def logout(request: Request):
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        get_core().sessions.invalidate(header.split(" ", 1)[1])
    return {"status": "logged out"}
