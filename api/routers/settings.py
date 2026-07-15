"""Settings router — masked key display, update, per-service test buttons.

Keys are stored encrypted (AES-256 via Rust core on the VPS). In demo/dev mode
we read presence from env vars only — never the values themselves.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import verify_session
from ..services import integrations

router = APIRouter(prefix="/api/admin/settings", tags=["settings"])


# (display_name, env_var, kind)
_KEY_FIELDS = [
    ("Anthropic API Key", "ANTHROPIC_API_KEY"),
    ("OpenAI API Key", "OPENAI_API_KEY"),
    ("Google AI Key", "GOOGLE_AI_API_KEY"),
    ("Higgsfield API Key", "HIGGSFIELD_API_KEY"),
    ("Buffer Access Token", "BUFFER_ACCESS_TOKEN"),
    ("Airtable API Key", "AIRTABLE_API_KEY"),
    ("Apify API Token", "APIFY_API_TOKEN"),
    ("Firecrawl API Key", "FIRECRAWL_API_KEY"),
    ("Telegram Bot Token", "TELEGRAM_BOT_TOKEN"),
    ("Email API Key", "EMAIL_API_KEY"),
]


def _mask(value: str) -> str:
    if not value:
        return ""
    last4 = value[-4:] if len(value) >= 4 else value
    return f"••••••••{last4}"


@router.get("")
async def get_settings(_=Depends(verify_session)) -> dict:
    keys = []
    for label, env in _KEY_FIELDS:
        val = os.getenv(env, "")
        keys.append(
            {"label": label, "env": env, "masked": _mask(val), "configured": bool(val)}
        )
    return {
        "active_llm_provider": os.getenv("ACTIVE_LLM_PROVIDER", "anthropic"),
        "hermes_max_children": int(os.getenv("HERMES_MAX_CHILDREN", "10")),
        "demo_mode": os.getenv("NEXT_PUBLIC_DEMO_MODE", "true") == "true",
        "keys": keys,
        "integrations": integrations.status(),
    }


class SettingUpdate(BaseModel):
    env: str
    value: str


@router.put("")
async def update_setting(payload: SettingUpdate, _=Depends(verify_session)) -> dict:
    """Update is handled by the VPS (writes encrypted value to Supabase
    `public.settings`). Returns the masked form so the dashboard can re-render.
    """
    return {
        "env": payload.env,
        "masked": _mask(payload.value),
        "configured": True,
        "message": "Saved. Restart the API to load new env values.",
    }


@router.post("/test/{service}")
async def test_service(service: str, _=Depends(verify_session)) -> dict:
    result = integrations.test(service)
    return result
