"""Integration status + test endpoints.

Each integration reports `configured` (env var present) and `test()` returns a
clear "set ENV_VAR to activate" message when not configured. None of these
make live network calls from this dev box — they only read env presence.
"""
from __future__ import annotations

import os

# (key, env_var, kind) — `kind` drives the test message.
_INTEGRATIONS = {
    "anthropic":   ("ANTHROPIC_API_KEY",   "AI provider"),
    "openai":      ("OPENAI_API_KEY",      "AI provider"),
    "google":      ("GOOGLE_AI_API_KEY",   "AI provider"),
    "ollama":      ("OLLAMA_BASE_URL",     "AI provider"),
    "higgsfield":  ("HIGGSFIELD_API_KEY",  "Video generation"),
    "buffer":      ("BUFFER_ACCESS_TOKEN", "Social publishing"),
    "airtable":    ("AIRTABLE_API_KEY",    "Client asset gallery"),
    "apify":       ("APIFY_API_TOKEN",     "Competitor scraping"),
    "firecrawl":   ("FIRECRAWL_API_KEY",   "Web scraping"),
    "telegram":    ("TELEGRAM_BOT_TOKEN",  "Voice control (Telegram)"),
    "email":       ("EMAIL_API_KEY",       "Transactional email"),
    "supabase":    ("SUPABASE_URL",        "Database"),
    "vercel":      ("VERCEL_TOKEN",        "Deploy"),
    "github":      ("GITHUB_TOKEN",        "Repo sync"),
}


def status() -> list[dict]:
    out = []
    for key, (env, kind) in _INTEGRATIONS.items():
        out.append(
            {
                "service": key,
                "kind": kind,
                "env_var": env,
                "configured": bool(os.getenv(env)),
            }
        )
    return out


def test(service: str) -> dict:
    if service not in _INTEGRATIONS:
        return {"service": service, "connected": False,
                "message": f"Unknown service '{service}'."}
    env, kind = _INTEGRATIONS[service]
    configured = bool(os.getenv(env))
    if configured:
        return {
            "service": service,
            "connected": True,
            "message": f"{kind.title()} key is set. Live test runs on the VPS.",
        }
    return {
        "service": service,
        "connected": False,
        "message": f"Set {env} in .env to activate {kind}. See docs/SECRETS.md.",
    }
