"""Shared auth + rate-limit dependencies for routers.

Production sessions and login attempt counters use Redis when ``REDIS_URL`` is
configured, so multiple Uvicorn workers share one security boundary. Local dev
without Redis retains the existing in-process core contract.
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Request

from .services.operator_sessions import (
    SessionBackendUnavailable,
    check_auth_rate_limit,
    issue_session as _issue_session,
    validate_session,
)
from .services.supabase_auth import authenticate_member, looks_like_jwt


def _trusted_proxies() -> set[str]:
    return {p.strip() for p in os.getenv("TRUSTED_PROXY_IPS", "").split(",") if p.strip()}


def _client_ip(request: Request) -> str:
    """Client IP for rate limiting.

    ``X-Forwarded-For`` is caller-controlled, so it is honoured only when the
    direct peer is a configured trusted proxy (``TRUSTED_PROXY_IPS``, e.g. the
    Next.js server or Caddy). Then the right-most hop that is not itself a
    trusted proxy is used, which a client cannot spoof by prepending values.
    """
    peer = request.client.host if request.client else "unknown"
    trusted = _trusted_proxies()
    if peer not in trusted:
        return peer
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return peer


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


async def verify_session(request: Request) -> str:
    """Dependency: 401 unless a valid Bearer credential is present.

    Accepts either a Supabase Auth access token (per-human ``user:<uuid>``
    identity with the workspace role on ``request.state.role``) or a legacy
    operator session token (only issuable while password login is enabled).
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = header.split(" ", 1)[1]
    if looks_like_jwt(token):
        return await authenticate_member(request, token)
    try:
        valid = validate_session(token)
    except SessionBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail="Authentication backend unavailable") from exc
    if not valid:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    request.state.identity = token
    request.state.role = "owner"  # legacy shared session: full rights
    return token
