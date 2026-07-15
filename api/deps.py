"""Shared auth + rate-limit dependencies for routers.

Lives at `api.deps` (NOT `api.routers._deps`) so it can import the core without
touching `api.app` — breaking the circular import (app imports routers,
routers imported deps, deps imported app).
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from .services.native import get_core


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def issue_session() -> str:
    return get_core().sessions.issue()


def rate_limit_auth(request: Request) -> None:
    """5 attempts/min per IP on auth verify. Raises 429 on excess."""
    key = f"auth:{_client_ip(request)}"
    allowed, retry = get_core().rate_limiter.check(key, capacity=5.0, rate=5.0 / 60.0)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(retry)},
        )


def verify_session(request: Request) -> str:
    """Dependency: 401 unless a valid Bearer token is present."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = header.split(" ", 1)[1]
    if not get_core().sessions.validate(token):
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return token
