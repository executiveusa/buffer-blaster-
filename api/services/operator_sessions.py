"""Production-safe operator session and auth-rate state.

When ``REDIS_URL`` is configured, sessions and auth attempt counters live in
Redis so multiple Uvicorn workers share one security boundary. Local tests and
single-process development keep using the existing native/Python core.

A configured-but-unreachable Redis is fail-closed: production must not silently
fall back to per-process sessions or per-worker rate limits.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Any

from .native import get_core

SESSION_TTL_SECONDS = 86_400
AUTH_WINDOW_SECONDS = 60
AUTH_ATTEMPTS_PER_WINDOW = 5
_SESSION_PREFIX = "stavarai:session:"
_AUTH_PREFIX = "stavarai:auth-rate:"


class SessionBackendUnavailable(RuntimeError):
    pass


_redis_client: Any | None = None
_redis_url: str | None = None


def _redis() -> Any | None:
    global _redis_client, _redis_url
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    if _redis_client is not None and _redis_url == url:
        return _redis_client
    try:
        import redis

        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
            health_check_interval=30,
        )
        client.ping()
    except Exception as exc:  # fail closed when production Redis is configured
        raise SessionBackendUnavailable("shared session backend unavailable") from exc
    _redis_client = client
    _redis_url = url
    return client


def issue_session() -> str:
    client = _redis()
    if client is None:
        return get_core().sessions.issue()
    token = secrets.token_urlsafe(32)
    try:
        client.setex(f"{_SESSION_PREFIX}{token}", SESSION_TTL_SECONDS, "1")
    except Exception as exc:
        raise SessionBackendUnavailable("shared session backend unavailable") from exc
    return token


def validate_session(token: str) -> bool:
    client = _redis()
    if client is None:
        return get_core().sessions.validate(token)
    try:
        return bool(client.exists(f"{_SESSION_PREFIX}{token}"))
    except Exception as exc:
        raise SessionBackendUnavailable("shared session backend unavailable") from exc


def invalidate_session(token: str) -> None:
    client = _redis()
    if client is None:
        get_core().sessions.invalidate(token)
        return
    try:
        client.delete(f"{_SESSION_PREFIX}{token}")
    except Exception as exc:
        raise SessionBackendUnavailable("shared session backend unavailable") from exc


def check_auth_rate_limit(client_ip: str) -> tuple[bool, int]:
    """Return ``(allowed, retry_after_seconds)`` for the login boundary."""
    client = _redis()
    if client is None:
        key = f"auth:{client_ip}"
        return get_core().rate_limiter.check(
            key,
            capacity=float(AUTH_ATTEMPTS_PER_WINDOW),
            rate=float(AUTH_ATTEMPTS_PER_WINDOW) / AUTH_WINDOW_SECONDS,
        )

    digest = hashlib.sha256(client_ip.encode("utf-8", "ignore")).hexdigest()[:24]
    window = int(time.time() // AUTH_WINDOW_SECONDS)
    key = f"{_AUTH_PREFIX}{digest}:{window}"
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, AUTH_WINDOW_SECONDS + 2)
        ttl = int(client.ttl(key))
    except Exception as exc:
        raise SessionBackendUnavailable("shared auth rate-limit backend unavailable") from exc
    return count <= AUTH_ATTEMPTS_PER_WINDOW, max(1, ttl if ttl > 0 else AUTH_WINDOW_SECONDS)


def backend_name() -> str:
    return "redis" if os.getenv("REDIS_URL", "").strip() else "process"
