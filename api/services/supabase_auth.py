"""Supabase Auth (GoTrue) human identities for the operator console.

Humans sign in through Supabase Auth on the frontend and send the resulting
access token (a GoTrue-issued JWT) as ``Authorization: Bearer``. This module
verifies that token locally (HS256, the self-hosted default) and resolves the
caller's workspace membership from migration 017's
``buffer_blaster.workspace_members`` through PostgREST using the service key.

Fail-closed everywhere: no configured secret, a bad signature, an expired or
wrong-audience token, an unreachable member store or a missing membership all
produce 401. Agents never pass through here; agent ``bba_`` tokens are handled
separately in ``integration_auth``.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
import uuid

import httpx
from fastapi import HTTPException, Request

from . import usage_wallet as _wallet

ROLES = ("owner", "approver", "operator", "viewer")
EXECUTE_ROLES = ("owner", "operator", "approver")
APPROVER_ROLES = ("owner", "approver")
EXPECTED_AUDIENCE = "authenticated"
_EXP_LEEWAY_SECONDS = 30


def looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def decode_supabase_jwt(token: str) -> dict | None:
    """Verify a GoTrue access token locally. Returns claims or None.

    Only HS256 is accepted: the self-hosted stack signs with JWT_SECRET, and
    accepting any other algorithm would open algorithm-confusion paths. When
    ``SUPABASE_JWT_SECRET`` is unset the JWT path is disabled entirely.
    """
    secret = os.getenv("SUPABASE_JWT_SECRET", "")
    if not secret:
        return None
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
    except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
        return None
    if header.get("alg") != "HS256":
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        supplied_sig = _b64url_decode(sig_b64)
    except (binascii.Error, ValueError):
        return None
    if not hmac.compare_digest(expected, supplied_sig):
        return None
    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except (json.JSONDecodeError, binascii.Error, ValueError, UnicodeDecodeError):
        return None
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or isinstance(exp, bool):
        return None
    if time.time() > float(exp) + _EXP_LEEWAY_SECONDS:
        return None
    aud = claims.get("aud")
    if isinstance(aud, str):
        aud_ok = hmac.compare_digest(aud, EXPECTED_AUDIENCE)
    elif isinstance(aud, list):
        aud_ok = EXPECTED_AUDIENCE in aud
    else:
        aud_ok = False
    if not aud_ok:
        return None
    issuer = os.getenv("SUPABASE_JWT_ISSUER", "").strip()
    if issuer and claims.get("iss") != issuer:
        return None
    try:
        claims["sub"] = str(uuid.UUID(str(claims.get("sub"))))
    except (ValueError, AttributeError, TypeError):
        return None
    return claims


async def fetch_member_role(user_id: str, workspace_id: str) -> str | None:
    """Live membership lookup through PostgREST (service key, schema-pinned).

    Returns the member's role or None. Membership is checked on every call so
    a removed member loses access immediately; the store being unreachable is
    indistinguishable from "not a member" (fail closed).
    """
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not (base and key and workspace_id):
        return None
    try:
        ws = str(uuid.UUID(str(workspace_id)))
        uid = str(uuid.UUID(str(user_id)))
    except (ValueError, AttributeError, TypeError):
        return None
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Accept-Profile": "buffer_blaster",
    }
    params = {"workspace_id": f"eq.{ws}", "user_id": f"eq.{uid}", "select": "role", "limit": "1"}
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            resp = await http.get(f"{base}/rest/v1/workspace_members", headers=headers, params=params)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        rows = resp.json()
    except ValueError:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    role = rows[0].get("role") if isinstance(rows[0], dict) else None
    return role if role in ROLES else None


async def authenticate_member(request: Request, token: str) -> str:
    """Validate a Supabase JWT and set the human identity on the request.

    Identity becomes ``user:<uuid>`` so approvals record the actual person in
    ``decided_by``. Raises 401 for every failure mode.
    """
    claims = decode_supabase_jwt(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        role = await fetch_member_role(claims["sub"], _wallet._workspace_id())
    except httpx.HTTPError:
        role = None
    if role is None or role not in ROLES:
        raise HTTPException(status_code=401, detail="Not a workspace member")
    identity = f"user:{claims['sub']}"
    request.state.identity = identity
    request.state.user_id = claims["sub"]
    request.state.role = role
    return identity
