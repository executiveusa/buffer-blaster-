"""Truthful integration status and non-destructive connection tests.

`configured` means the required local configuration exists. `verified` means a
real provider handshake succeeded during this request. We never report a
provider as connected merely because an environment variable is present.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


# service -> (primary env var, kind)
_INTEGRATIONS = {
    "anthropic": ("ANTHROPIC_API_KEY", "AI provider"),
    "openai": ("OPENAI_API_KEY", "AI provider"),
    "google": ("GOOGLE_AI_API_KEY", "AI provider"),
    "ollama": ("OLLAMA_BASE_URL", "AI provider"),
    "fal": ("FAL_KEY", "Media generation"),
    "higgsfield": ("HIGGSFIELD_API_KEY", "Legacy video generation"),
    "buffer": ("BUFFER_ACCESS_TOKEN", "Legacy social publishing"),
    "airtable": ("AIRTABLE_API_KEY", "Client asset gallery"),
    "apify": ("APIFY_API_TOKEN", "Competitor scraping"),
    "firecrawl": ("FIRECRAWL_API_KEY", "Web scraping"),
    "telegram": ("TELEGRAM_BOT_TOKEN", "Voice control (Telegram)"),
    "email": ("EMAIL_API_KEY", "Transactional email"),
    "supabase": ("SUPABASE_SERVICE_KEY", "Database"),
    "vercel": ("VERCEL_TOKEN", "Deploy"),
    "github": ("GITHUB_TOKEN", "Repo sync"),
}


def _configured(service: str) -> bool:
    if service == "supabase":
        return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))
    env, _ = _INTEGRATIONS[service]
    return bool(os.getenv(env))


def status() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, (env, kind) in _INTEGRATIONS.items():
        configured = _configured(key)
        out.append(
            {
                "service": key,
                "kind": kind,
                "env_var": env,
                "configured": configured,
                "verified": False,
                "state": "configured_unverified" if configured else "not_configured",
            }
        )
    return out


async def _verify_openai(client: httpx.AsyncClient, key: str) -> httpx.Response:
    return await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})


async def _verify_anthropic(client: httpx.AsyncClient, key: str) -> httpx.Response:
    return await client.get(
        "https://api.anthropic.com/v1/models?limit=1",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
    )


async def _verify_google(client: httpx.AsyncClient, key: str) -> httpx.Response:
    return await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key})


async def _verify_ollama(client: httpx.AsyncClient, base_url: str) -> httpx.Response:
    return await client.get(f"{base_url.rstrip('/')}/api/tags")


async def _verify_supabase(client: httpx.AsyncClient, key: str) -> httpx.Response:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    return await client.get(
        f"{base}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )


async def test(service: str) -> dict[str, Any]:
    if service not in _INTEGRATIONS:
        return {
            "service": service,
            "configured": False,
            "verified": False,
            "state": "unknown_service",
            "message": f"Unknown service '{service}'.",
        }

    env, kind = _INTEGRATIONS[service]
    if not _configured(service):
        missing = [env]
        if service == "supabase" and not os.getenv("SUPABASE_URL"):
            missing.insert(0, "SUPABASE_URL")
        return {
            "service": service,
            "configured": False,
            "verified": False,
            "state": "not_configured",
            "missing": missing,
            "message": f"Configure {', '.join(missing)} to activate {kind}.",
        }

    key = os.getenv(env, "")
    verifiers = {
        "openai": _verify_openai,
        "anthropic": _verify_anthropic,
        "google": _verify_google,
        "ollama": _verify_ollama,
        "supabase": _verify_supabase,
    }
    verifier = verifiers.get(service)
    if verifier is None:
        return {
            "service": service,
            "configured": True,
            "verified": False,
            "state": "configured_unverified",
            "message": f"{kind} configuration is present, but this adapter has no safe read-only handshake yet.",
        }

    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await verifier(client, key)
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "service": service,
            "configured": True,
            "verified": False,
            "state": "handshake_failed",
            "message": f"{kind} handshake failed.",
            "detail": type(exc).__name__,
        }

    if response.is_success:
        return {
            "service": service,
            "configured": True,
            "verified": True,
            "state": "verified",
            "message": f"{kind} handshake succeeded.",
            "status": response.status_code,
        }
    return {
        "service": service,
        "configured": True,
        "verified": False,
        "state": "handshake_failed",
        "message": f"{kind} handshake returned HTTP {response.status_code}.",
        "status": response.status_code,
    }
