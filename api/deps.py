"""Shared auth + rate-limit dependencies for routers.

Production sessions and login attempt counters use Redis when ``REDIS_URL`` is
configured, so multiple Uvicorn workers share one security boundary. Local dev
without Redis retains the existing in-process core contract.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from .services.operator_sessions import (
    SessionBackendUnavailable,
    check_auth_rate_limit,
    issue_session as _issue_session,
    validate_session,
)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def issue_session() -> str:
    try:
        return _issue_session()
    except SessionBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail="Authentication backend unavailable") from exc


def rate_limit_auth(request: Request) -> None:
    """Five attempts/minute per source IP; shared through Redis in production."""
    try:
        allowed, retry = check_auth_rate_limit(_client_ip(request))
    except SessionBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail="Authentication backend unavailable") from exc
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
    try:
        valid = validate_session(token)
    except SessionBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail="Authentication backend unavailable") from exc
    if not valid:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return token
