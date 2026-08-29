"""Operator settings and integration verification.

Secrets remain runtime-environment managed and are never accepted through this
API. Safe operator settings use the shared Redis runtime store. Integration
verification distinguishes local configuration from a real provider handshake.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import verify_session
from ..services import integrations, runtime_settings

router = APIRouter(prefix="/api/admin/settings", tags=["settings"])

_KEY_FIELDS = [
    ("Anthropic API Key", "ANTHROPIC_API_KEY"),
    ("OpenAI API Key", "OPENAI_API_KEY"),
    ("Google AI Key", "GOOGLE_AI_API_KEY"),
    ("Fal API Key", "FAL_KEY"),
    ("Supabase Service Key", "SUPABASE_SERVICE_KEY"),
    ("Stripe Secret Key", "STRIPE_SECRET_KEY"),
    ("7-Day Trial Stripe Price", "STRIPE_TRIAL_7_PRICE_ID"),
    ("30-Day Trial Stripe Price", "STRIPE_TRIAL_30_PRICE_ID"),
    ("Starter Stripe Price", "STRIPE_STARTER_PRICE_ID"),
    ("Pro Stripe Price", "STRIPE_PRO_PRICE_ID"),
    ("Higgsfield API Key (legacy)", "HIGGSFIELD_API_KEY"),
    ("Airtable API Key", "AIRTABLE_API_KEY"),
    ("Apify API Token", "APIFY_API_TOKEN"),
    ("Firecrawl API Key", "FIRECRAWL_API_KEY"),
    ("Telegram Bot Token", "TELEGRAM_BOT_TOKEN"),
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
        keys.append({"label": label, "env": env, "masked": _mask(val), "configured": bool(val)})
    active_provider = await runtime_settings.get_value("ACTIVE_LLM_PROVIDER", "anthropic")
    max_children = await runtime_settings.get_value("AGENT_MAX_CHILDREN", "10")
    try:
        max_children_int = int(max_children)
    except ValueError:
        max_children_int = 10
    return {
        "active_llm_provider": active_provider,
        "operator_max_children": max_children_int,
        "demo_mode": os.getenv("NEXT_PUBLIC_DEMO_MODE", "false") == "true",
        "keys": keys,
        "integrations": integrations.status(),
        "secret_updates": "environment_only",
        "runtime_settings_store": "redis" if os.getenv("REDIS_URL") else "unavailable",
    }


class SettingUpdate(BaseModel):
    env: str
    value: str


@router.put("")
async def update_setting(payload: SettingUpdate, _=Depends(verify_session)) -> dict:
    result = await runtime_settings.set_value(payload.env, payload.value)
    if result.get("ok"):
        return result
    error = str(result.get("error") or "setting_update_failed")
    if error == "setting_not_runtime_editable":
        raise HTTPException(
            status_code=409,
            detail="Secrets and deployment configuration are environment-managed. Only ACTIVE_LLM_PROVIDER and AGENT_MAX_CHILDREN are editable here.",
        )
    if error in {"runtime_store_unavailable", "runtime_store_write_failed"}:
        raise HTTPException(status_code=503, detail=result.get("message") or error)
    raise HTTPException(status_code=422, detail=result)


@router.post("/test/{service}")
async def test_service(service: str, _=Depends(verify_session)) -> dict:
    return await integrations.test(service)
