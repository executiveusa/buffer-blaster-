"""Authentication helper shared by REST, MCP, CLI, and agent plugins.

Identities:
- ``api-key``: the operator key (human/owner, break-glass). Full rights.
- console session: legacy shared human identity (only issuable when
  ``DEMO_PASSWORD_LOGIN_ENABLED`` is set). Full rights.
- ``user:<uuid>``: a Supabase Auth human. Role comes live from
  ``buffer_blaster.workspace_members`` (owner/approver/operator/viewer).
- ``agent:<token_id>``: a scoped ``bba_`` agent token. Can never grant
  approvals and needs a human-issued approval for any spend or publish.
"""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from ..deps import verify_session
from .agent_access import SCOPES, TOKEN_PREFIX, is_agent, verify_agent_token
from .supabase_auth import APPROVER_ROLES, EXECUTE_ROLES, ROLES, authenticate_member, looks_like_jwt

# Agent tokens are default-deny: only these surfaces accept them. Wallet
# creation, billing activation, the money loop (ad activation) and every
# settings/admin route stay human-only.
AGENT_ALLOWED_PREFIXES = ("/api/mcp", "/api/studio/", "/api/agent/")
AGENT_DENIED_PREFIXES = (
    "/api/studio/billing/activate",
    "/api/studio/billing/internal-wallet",
    "/api/studio/money-loop",
    "/api/agent/tokens",
)


def _agent_path_allowed(path: str) -> bool:
    if any(path.startswith(p) for p in AGENT_DENIED_PREFIXES):
        return False
    return any(path.startswith(p) for p in AGENT_ALLOWED_PREFIXES)


def _supplied_credential(request: Request) -> str:
    bearer = request.headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        return bearer.split(" ", 1)[1].strip()
    return request.headers.get("x-api-key", "").strip()


async def verify_operator(request: Request) -> str:
    expected = os.getenv("BLASTER_API_KEY", "")
    supplied = _supplied_credential(request)
    if supplied.startswith(TOKEN_PREFIX):
        agent = await verify_agent_token(supplied)
        if not agent:
            raise HTTPException(status_code=401, detail="Unauthorized")
        identity = f"agent:{agent['id']}"
        request.state.identity = identity
        request.state.scopes = set(agent["scopes"])
        request.state.agent_name = agent.get("name")
        path = request.url.path
        if not _agent_path_allowed(path):
            raise HTTPException(status_code=403, detail="Not available to agent tokens")
        if path.startswith("/api/studio/"):
            needed = {"read"} if request.method in {"GET", "HEAD"} else {"plan", "render", "publish"}
            if not needed & request.state.scopes:
                raise HTTPException(status_code=403, detail=f"Agent token lacks scope: {'/'.join(sorted(needed))}")
        return identity
    if expected and supplied and hmac.compare_digest(expected, supplied):
        request.state.identity = "api-key"
        request.state.role = "owner"  # break-glass owner credential
        request.state.scopes = set(SCOPES)
        return "api-key"
    if looks_like_jwt(supplied):
        identity = await authenticate_member(request, supplied)
        request.state.scopes = set(SCOPES)
        return identity
    try:
        identity = await verify_session(request)
    except HTTPException:
        if not expected:
            raise HTTPException(status_code=503, detail="Operator API auth is not configured")
        raise HTTPException(status_code=401, detail="Unauthorized")
    request.state.identity = identity
    request.state.role = "owner"  # legacy shared session: full rights
    request.state.scopes = set(SCOPES)
    return identity


def request_scopes(request: Request) -> set[str]:
    return set(getattr(request.state, "scopes", set()))


def request_role(request: Request) -> str | None:
    role = getattr(request.state, "role", None)
    return role if role in ROLES else None


def require_role(request: Request, *roles: str) -> None:
    """403 unless the caller is a human whose workspace role is allowed.

    Agents carry no role, so this also denies them whenever it runs.
    """
    role = request_role(request)
    if role is None or role not in roles:
        raise HTTPException(status_code=403, detail=f"Requires role: {'/'.join(roles)}")


def require_execute_role(request: Request) -> None:
    """``approved=true`` execution (paid runs, publishing): no viewers."""
    require_role(request, *EXECUTE_ROLES)


def require_approver_role(request: Request) -> None:
    """Approval decisions and agent-token management: owners/approvers."""
    require_role(request, *APPROVER_ROLES)


def require_human_write(request: Request, identity: str) -> None:
    """Viewers are read-only: mutating or provider-invoking routes need an
    execute role. Agents are unaffected here - their ``bba_`` scope checks
    already ran inside ``verify_operator``.
    """
    if not is_agent(identity):
        require_execute_role(request)


def require_scope(request: Request, scope: str) -> None:
    if scope not in request_scopes(request):
        raise HTTPException(status_code=403, detail=f"Agent token lacks scope: {scope}")


async def verify_human_operator(request: Request) -> str:
    """Only a human identity (operator key or console session) may pass."""
    identity = await verify_operator(request)
    if is_agent(identity):
        raise HTTPException(status_code=403, detail="Human operator required")
    return identity
