"""Authentication helper shared by REST, MCP, CLI, and agent plugins."""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from ..deps import verify_session


def verify_operator(request: Request) -> str:
    expected = os.getenv("BLASTER_API_KEY", "")
    bearer = request.headers.get("Authorization", "")
    supplied = request.headers.get("x-api-key", "")
    if bearer.startswith("Bearer "):
        supplied = bearer.split(" ", 1)[1]
    if expected and supplied and hmac.compare_digest(expected, supplied):
        return "api-key"
    try:
        return verify_session(request)
    except HTTPException:
        if not expected:
            raise HTTPException(status_code=503, detail="Operator API auth is not configured")
        raise HTTPException(status_code=401, detail="Unauthorized")
