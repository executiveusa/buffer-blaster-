"""S5: footage source connectors - Google Drive, OneDrive, Dropbox Chooser.

Security contract:
- OAuth tokens are encrypted at rest with the platform AES-256-GCM core
  (``MASTER_ENCRYPTION_KEY`` via ``native.get_core().encryption``) and are
  NEVER returned by any function in this module. Responses carry presence
  booleans, scopes and expiry only.
- Dropbox uses the client-side Chooser: the browser receives a direct file
  link, and this service stores no token at all. Revoke is a no-op.
- Connection state is keyed per workspace (``STUDIO_WORKSPACE_ID``): one
  workspace's tokens are never readable or usable under another workspace.

Review current vendor OAuth requirements before configuring a connection.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import redis.asyncio as redis

from . import native

log = logging.getLogger(__name__)

PROVIDERS = ("google", "onedrive", "dropbox")

# Verified 2026-11-10 (see FOOTAGE_VENDOR_VERIFICATION.md):
# - Google Picker API returns selected file metadata to the app; the drive.file
#   scope covers files the user picks/opens with the app.
# - Dropbox Chooser returns a direct link; no OAuth token is needed or stored.
# - OneDrive File Picker v8 uses delegated Graph permissions (Files.Read).
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_GOOGLE_SCOPE = "https://www.googleapis.com/auth/drive.file"
_ONEDRIVE_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
_ONEDRIVE_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
_ONEDRIVE_SCOPES = ("offline_access", "Files.Read")

_STATE_TTL_S = 600


def _workspace_id() -> str:
    return os.getenv("STUDIO_WORKSPACE_ID", "ws-default")


def _redis():
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def _conn_key(workspace_id: str, provider: str) -> str:
    return f"bb:footage:conn:{workspace_id}:{provider}"


def _state_key(state: str) -> str:
    return f"bb:footage:state:{state}"


def _enc() -> native.Encryption:
    return native.get_core().encryption


def _redirect_base() -> str:
    return os.getenv("FOOTAGE_OAUTH_REDIRECT_BASE", "http://localhost:8000")


def _client_config(provider: str) -> dict[str, str]:
    if provider == "google":
        return {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        }
    if provider == "onedrive":
        return {
            "client_id": os.getenv("ONEDRIVE_CLIENT_ID", ""),
            "client_secret": os.getenv("ONEDRIVE_CLIENT_SECRET", ""),
        }
    return {"client_id": os.getenv("DROPBOX_APP_KEY", ""), "client_secret": ""}


def provider_status() -> dict[str, Any]:
    """Which providers are configured (env present). No secret material."""
    out: dict[str, Any] = {}
    for p in PROVIDERS:
        cfg = _client_config(p)
        if p == "dropbox":
            out[p] = {"mode": "chooser", "configured": bool(cfg["client_id"]),
                      "stores_token": False}
        else:
            out[p] = {"mode": "oauth", "configured": bool(cfg["client_id"] and cfg["client_secret"]),
                      "stores_token": True}
    return {"ok": True, "providers": out}


async def consent_url(provider: str, *, actor: str) -> dict[str, Any]:
    """Build the user-consent URL. Returns the URL and one-time state only.

    Dropbox has no consent URL (Chooser runs fully client-side); callers get
    the app key for the embed instead.
    """
    if provider not in PROVIDERS:
        return {"ok": False, "error": "unknown_provider", "allowed": list(PROVIDERS)}
    cfg = _client_config(provider)
    if provider == "dropbox":
        if not cfg["client_id"]:
            return {"ok": False, "error": "provider_not_configured", "provider": provider}
        return {"ok": True, "provider": provider, "mode": "chooser",
                "chooser_app_key": cfg["client_id"], "consent_url": None,
                "note": "Dropbox Chooser runs in the browser and returns direct links; no token is stored."}
    if not (cfg["client_id"] and cfg["client_secret"]):
        return {"ok": False, "error": "provider_not_configured", "provider": provider}

    state = secrets.token_urlsafe(24)
    # PKCE (live-verified 2026-11-10): Google documents S256 for the auth-code
    # flow; the Microsoft identity platform recommends PKCE for ALL client
    # types. Verifier is 43-128 unreserved chars; challenge is the base64url
    # (no padding) SHA-256 of the verifier. The verifier never leaves the
    # server except inside the token exchange.
    code_verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    await _redis().setex(_state_key(state), _STATE_TTL_S,
                         json.dumps({"workspace_id": _workspace_id(), "provider": provider,
                                     "actor": actor, "code_verifier": code_verifier}))
    if provider == "google":
        query = {
            "client_id": cfg["client_id"],
            "redirect_uri": f"{_redirect_base()}/api/studio/footage/callback/google",
            "response_type": "code",
            "scope": _GOOGLE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{_GOOGLE_AUTH_URL}?{urlencode(query)}"
    else:
        query = {
            "client_id": cfg["client_id"],
            "redirect_uri": f"{_redirect_base()}/api/studio/footage/callback/onedrive",
            "response_type": "code",
            "scope": " ".join(_ONEDRIVE_SCOPES),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = f"{_ONEDRIVE_AUTH_URL}?{urlencode(query)}"
    return {"ok": True, "provider": provider, "mode": "oauth", "consent_url": url, "state": state}


async def _post_form(url: str, data: dict[str, str], http: Any = None) -> dict[str, Any]:
    """One form POST; injectable for tests. Returns the parsed JSON body."""
    if http is not None:
        resp = await http("POST", url, data=data)
    else:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data=data)
    status = getattr(resp, "status_code", 200)
    body = resp.json()
    if status >= 400:
        return {"ok": False, "error": "provider_error", "status": status,
                "detail": body.get("error_description") or body.get("error") or "exchange_failed"}
    body["ok"] = True
    return body


async def complete_connect(provider: str, *, code: str, state: str, actor: str,
                           http: Any = None) -> dict[str, Any]:
    """Exchange an OAuth code and store the tokens encrypted. Tokens never
    appear in the return value."""
    if provider not in ("google", "onedrive"):
        return {"ok": False, "error": "provider_has_no_oauth", "provider": provider}
    cfg = _client_config(provider)
    if not (cfg["client_id"] and cfg["client_secret"]):
        return {"ok": False, "error": "provider_not_configured", "provider": provider}

    r = _redis()
    raw = await r.get(_state_key(state))
    if not raw:
        return {"ok": False, "error": "state_invalid_or_expired"}
    await r.delete(_state_key(state))  # single-use
    expected = json.loads(raw)
    # State binds provider + workspace + initiating actor; anything else is
    # not the round-trip this server started.
    if (expected["provider"] != provider or expected["workspace_id"] != _workspace_id()
            or expected["actor"] != actor):
        return {"ok": False, "error": "state_mismatch"}

    token_url = _GOOGLE_TOKEN_URL if provider == "google" else _ONEDRIVE_TOKEN_URL
    data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"{_redirect_base()}/api/studio/footage/callback/{provider}",
        "code_verifier": expected["code_verifier"],  # PKCE
    }
    token = await _post_form(token_url, data, http=http)
    if not token.get("ok") or not token.get("access_token"):
        return {"ok": False, "error": token.get("error", "exchange_failed"),
                "detail": token.get("detail")}

    enc = _enc()
    expires_in = int(token.get("expires_in") or 3600)
    record = {
        "provider": provider,
        "workspace_id": expected["workspace_id"],
        "token_ciphertext": enc.encrypt(str(token["access_token"])),
        "refresh_ciphertext": enc.encrypt(str(token["refresh_token"])) if token.get("refresh_token") else None,
        "scopes": token.get("scope", "").split() if token.get("scope") else list(_ONEDRIVE_SCOPES) if provider == "onedrive" else [_GOOGLE_SCOPE],
        "expires_at": int(time.time()) + expires_in,
        "connected_by": actor,
        "connected_at": int(time.time()),
    }
    await r.set(_conn_key(expected["workspace_id"], provider), json.dumps(record))
    mirror = await _mirror_connection(record)
    return {"ok": True, "provider": provider, "connected": True,
            "scopes": record["scopes"], "expires_at": record["expires_at"],
            "connected_by": actor,
            "mirror": mirror.get("status", "written") if mirror.get("ok") else "backlogged",
            "mirror_error": None if mirror.get("ok") else mirror.get("error")}


_MIRROR_BACKLOG = "bb:footage:mirror_backlog"


async def _mirror_connection(record: dict[str, Any]) -> dict[str, Any]:
    """PostgREST mirror (ciphertext columns only). Observable, never silent:
    failures are logged and durable-backlogged; the caller surfaces the
    outcome in its response."""
    try:
        import os as _os
        import httpx as _httpx
        base = _os.getenv("SUPABASE_URL", "").rstrip("/")
        key = _os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not (base and key):
            return {"ok": True, "status": "skipped_unconfigured"}
        row = {
            "workspace_id": record["workspace_id"],
            "provider": record["provider"],
            "status": "connected",
            "token_ciphertext": record["token_ciphertext"],
            "refresh_ciphertext": record["refresh_ciphertext"],
            "scopes": record["scopes"],
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record["expires_at"])) if record.get("expires_at") else None,
            "connected_by": record["connected_by"],
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        headers = {"apikey": key, "Authorization": f"Bearer {key}",
                   "Content-Profile": "buffer_blaster", "Prefer": "resolution=merge-duplicates"}
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{base}/rest/v1/footage_connections", headers=headers, json=row)
        if resp.status_code >= 300:
            log.error("footage connection mirror rejected: status=%s", resp.status_code)
            await _backlog_mirror({"action": "upsert", "row": row})
            return {"ok": False, "error": "mirror_rejected", "status": resp.status_code}
        return {"ok": True, "status": "written"}
    except Exception as exc:
        log.error("footage connection mirror failed: %s", type(exc).__name__)
        await _backlog_mirror({"action": "upsert", "row": {
            "workspace_id": record.get("workspace_id"), "provider": record.get("provider")}})
        return {"ok": False, "error": "mirror_unreachable", "detail": type(exc).__name__}


async def _backlog_mirror(payload: dict[str, Any]) -> None:
    """Durable record that a mirror write is owed; operators can replay."""
    try:
        await _redis().rpush(_MIRROR_BACKLOG, json.dumps(
            {**payload, "backlogged_at": int(time.time())}))
    except Exception:
        log.error("footage mirror backlog write failed", exc_info=True)


async def _load_record(provider: str, workspace_id: str | None = None) -> dict[str, Any] | None:
    ws = workspace_id or _workspace_id()
    raw = await _redis().get(_conn_key(ws, provider))
    if not raw:
        return None
    record = json.loads(raw)
    if record.get("workspace_id") != ws:
        return None  # per-workspace isolation, belt and braces on the key prefix
    return record


async def connection_status(*, workspace_id: str | None = None) -> dict[str, Any]:
    """Presence metadata only. NEVER includes token material."""
    ws = workspace_id or _workspace_id()
    out: dict[str, Any] = {"ok": True, "workspace_id": ws, "connections": {}}
    for p in PROVIDERS:
        if p == "dropbox":
            out["connections"][p] = {"connected": False, "mode": "chooser", "stores_token": False,
                                     "note": "Chooser links carry their own access; nothing is stored."}
            continue
        rec = await _load_record(p, ws)
        if not rec:
            out["connections"][p] = {"connected": False, "mode": "oauth"}
            continue
        out["connections"][p] = {
            "connected": True, "mode": "oauth", "stores_token": True,
            "scopes": rec["scopes"], "expires_at": rec["expires_at"],
            "connected_by": rec["connected_by"], "connected_at": rec["connected_at"],
        }
    return out


async def revoke(provider: str, *, actor: str, http: Any = None) -> dict[str, Any]:
    """Disconnect a provider: best-effort upstream revoke, then delete local
    state. Dropbox stores nothing, so revoke is a documented no-op."""
    if provider not in PROVIDERS:
        return {"ok": False, "error": "unknown_provider", "allowed": list(PROVIDERS)}
    if provider == "dropbox":
        return {"ok": True, "provider": provider, "revoked": True,
                "note": "Dropbox Chooser stores no token; nothing to revoke server-side."}
    ws = _workspace_id()
    rec = await _load_record(provider, ws)
    if not rec:
        return {"ok": True, "provider": provider, "revoked": True, "was_connected": False}
    upstream = None
    if provider == "google":
        # Best-effort upstream revoke; local delete happens regardless.
        try:
            plaintext = _enc().decrypt(rec["token_ciphertext"])
            resp = await _post_form(_GOOGLE_REVOKE_URL, {"token": plaintext}, http=http)
            upstream = "revoked" if resp.get("ok") else resp.get("error", "provider_error")
        except Exception:
            upstream = "unreachable"
    else:
        upstream = "local_only"  # Microsoft Graph has no token-revoke endpoint; deleting local state is the disconnect.
    await _redis().delete(_conn_key(ws, provider))
    mirror = await _mirror_revoked(ws, provider)
    return {"ok": True, "provider": provider, "revoked": True, "was_connected": True,
            "upstream": upstream,
            "mirror": mirror.get("status", "written") if mirror.get("ok") else "backlogged",
            "mirror_error": None if mirror.get("ok") else mirror.get("error")}


async def _mirror_revoked(workspace_id: str, provider: str) -> dict[str, Any]:
    """Delete the mirrored connection row. Observable, never silent."""
    try:
        import os as _os
        import httpx as _httpx
        base = _os.getenv("SUPABASE_URL", "").rstrip("/")
        key = _os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not (base and key):
            return {"ok": True, "status": "skipped_unconfigured"}
        headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Profile": "buffer_blaster"}
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{base}/rest/v1/footage_connections",
                headers=headers,
                params={"workspace_id": f"eq.{workspace_id}", "provider": f"eq.{provider}"})
        if resp.status_code >= 300:
            log.error("footage revoke mirror rejected: status=%s", resp.status_code)
            await _backlog_mirror({"action": "delete", "row": {"workspace_id": workspace_id, "provider": provider}})
            return {"ok": False, "error": "mirror_rejected", "status": resp.status_code}
        return {"ok": True, "status": "written"}
    except Exception as exc:
        log.error("footage revoke mirror failed: %s", type(exc).__name__)
        await _backlog_mirror({"action": "delete", "row": {"workspace_id": workspace_id, "provider": provider}})
        return {"ok": False, "error": "mirror_unreachable", "detail": type(exc).__name__}


async def _access_token(provider: str, http: Any = None) -> dict[str, Any]:
    """Internal only: decrypt (and lazily refresh) the access token. The
    plaintext returned here must never be placed in a response body."""
    rec = await _load_record(provider)
    if not rec:
        return {"ok": False, "error": "not_connected", "provider": provider}
    enc = _enc()
    if rec.get("expires_at") and rec["expires_at"] <= int(time.time()) + 60 and rec.get("refresh_ciphertext"):
        cfg = _client_config(provider)
        token_url = _GOOGLE_TOKEN_URL if provider == "google" else _ONEDRIVE_TOKEN_URL
        refresh = enc.decrypt(rec["refresh_ciphertext"])
        resp = await _post_form(token_url, {
            "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
            "refresh_token": refresh, "grant_type": "refresh_token",
        }, http=http)
        if not resp.get("ok") or not resp.get("access_token"):
            return {"ok": False, "error": "refresh_failed", "detail": resp.get("detail") or resp.get("error")}
        rec["token_ciphertext"] = enc.encrypt(str(resp["access_token"]))
        if resp.get("refresh_token"):
            rec["refresh_ciphertext"] = enc.encrypt(str(resp["refresh_token"]))
        rec["expires_at"] = int(time.time()) + int(resp.get("expires_in") or 3600)
        await _redis().set(_conn_key(rec["workspace_id"], provider), json.dumps(rec))
        await _mirror_connection(rec)
    return {"ok": True, "access_token": enc.decrypt(rec["token_ciphertext"])}


# ------------------------------------------------------ picker consent (S5 r2)
#
# USER REQUIREMENT: only files the user explicitly picks may be imported.
# There is NO whole-drive listing or arbitrary file_id import: a human picks
# a file in the provider's own picker (Google Picker / OneDrive file picker /
# Dropbox Chooser), the picker callback registers consent bound to the
# workspace and the human actor, and the import worker refuses anything else.


def _picked_key(workspace_id: str, provider: str, file_ref: str) -> str:
    return f"bb:footage:picked:{workspace_id}:{provider}:{file_ref}"


async def register_picked_file(provider: str, *, file_ref: str, filename: str,
                               actor: str) -> dict[str, Any]:
    """Register human picker consent for ONE file (file_id for google/onedrive,
    the chooser link for dropbox). Bound to this workspace and the actor."""
    if provider not in PROVIDERS:
        return {"ok": False, "error": "unknown_provider", "allowed": list(PROVIDERS)}
    if not file_ref or len(file_ref) > 2048 or not filename:
        return {"ok": False, "error": "file_ref_and_filename_required"}
    ws = _workspace_id()
    entry = {"provider": provider, "workspace_id": ws, "file_ref": file_ref,
             "filename": filename[:255], "picked_by": actor, "picked_at": int(time.time())}
    await _redis().set(_picked_key(ws, provider, file_ref), json.dumps(entry))
    return {"ok": True, "provider": provider, "file_ref": file_ref, "consented": True}


async def unpick_file(provider: str, *, file_ref: str) -> dict[str, Any]:
    ws = _workspace_id()
    await _redis().delete(_picked_key(ws, provider, file_ref))
    return {"ok": True, "provider": provider, "file_ref": file_ref, "consented": False}


async def is_file_consented(provider: str, file_ref: str | None) -> bool:
    if not file_ref:
        return False
    return bool(await _redis().get(_picked_key(_workspace_id(), provider, file_ref)))


async def list_files(provider: str, *, http: Any = None, limit: int = 50) -> dict[str, Any]:
    """List ONLY the files a human has picker-consented in this workspace.
    Never calls the provider to browse the drive - that would expose files
    the user did not pick. The consented file's metadata comes from the
    picker callback, not from a provider listing API."""
    if provider not in PROVIDERS:
        return {"ok": False, "error": "unknown_provider", "allowed": list(PROVIDERS)}
    ws = _workspace_id()
    r = _redis()
    files = []
    cursor = 0
    pattern = _picked_key(ws, provider, "*")
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
        for key in keys:
            raw = await r.get(key)
            if raw:
                entry = json.loads(raw)
                files.append({"id": entry["file_ref"], "name": entry["filename"],
                              "picked_by": entry["picked_by"], "picked_at": entry["picked_at"]})
        if cursor == 0 or len(files) >= limit:
            break
    files = files[:limit]
    return {"ok": True, "provider": provider, "files": files,
            "note": "Only human-picked files are listed; there is no whole-drive browse."}


async def download_target(provider: str, *, file_id: str | None = None,
                          link: str | None = None, http: Any = None) -> dict[str, Any]:
    """Internal: resolve the authenticated download URL + headers for the
    import worker. Never exposed through a route or MCP tool."""
    if provider == "dropbox":
        if not link:
            return {"ok": False, "error": "link_required"}
        return {"ok": True, "url": link, "headers": {}}
    if not file_id:
        return {"ok": False, "error": "file_id_required"}
    tok = await _access_token(provider, http=http)
    if not tok.get("ok"):
        return tok
    headers = {"Authorization": f"Bearer {tok['access_token']}"}
    if provider == "google":
        return {"ok": True, "url": f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", "headers": headers}
    return {"ok": True, "url": f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content", "headers": headers}
