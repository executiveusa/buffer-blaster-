"""S4 model/reasoning controls: provider, model and reasoning level resolved
per job > per workflow step > per workspace > env default.

Reasoning parameter mapping (review current vendor schemas before enabling):
- OpenRouter: `reasoning` object (effort|max_tokens) - openrouter.ai/docs/use-cases/reasoning-tokens
- OpenAI-compatible: `reasoning_effort` (Chat Completions) / `reasoning.effort` (Responses) - platform.openai.com/docs/guides/reasoning
- Anthropic: `thinking` (extended thinking is legacy on Claude 4.7+; adaptive recommended) - docs.anthropic.com/en/docs/build-with-claude/extended-thinking
Unknown provider + requested reasoning level is REJECTED, never guessed.
"""
from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as redis

from . import runtime_settings
from .llm_adapter import active_model, active_provider

REASONING_PARAMS: dict[str, str] = {
    "openrouter": "reasoning",
    "openai": "reasoning_effort",
    "openai-compatible": "reasoning_effort",
    "anthropic": "thinking",
}

REASONING_LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")

_SETTING_KEYS = ("MODEL_PROVIDER", "MODEL_NAME", "MODEL_REASONING_LEVEL")


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def _workspace_id() -> str:
    return os.getenv("STUDIO_WORKSPACE_ID", "").strip() or os.getenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-default")


def _step_key(step: str) -> str:
    # Workspace-scoped: one workspace's step config never leaks into another's.
    return f"buffer_blaster:modelcfg:{_workspace_id()}:step:{step}"


async def set_step_config(step: str, *, provider: str | None = None, model: str | None = None,
                          reasoning_level: str | None = None) -> dict[str, Any]:
    if not step:
        return {"ok": False, "error": "step_required"}
    if reasoning_level is not None and reasoning_level not in REASONING_LEVELS:
        return {"ok": False, "error": "invalid_reasoning_level", "allowed": list(REASONING_LEVELS)}
    url = _redis_url()
    if not url:
        return {"ok": False, "error": "settings_store_unavailable"}
    client = redis.from_url(url, decode_responses=True)
    try:
        mapping = {k: v for k, v in {"provider": provider, "model": model,
                                     "reasoning_level": reasoning_level}.items() if v}
        if not mapping:
            return {"ok": False, "error": "nothing_to_set"}
        await client.hset(_step_key(step), mapping=mapping)
        return {"ok": True, "step": step, **mapping}
    except redis.RedisError as exc:
        return {"ok": False, "error": "settings_write_failed", "detail": type(exc).__name__}
    finally:
        await client.aclose()


async def _step_config(step: str) -> dict[str, str]:
    url = _redis_url()
    if not url:
        return {}
    client = redis.from_url(url, decode_responses=True)
    try:
        return dict(await client.hgetall(_step_key(step)) or {})
    except redis.RedisError:
        return {}
    finally:
        await client.aclose()


async def _workspace_config() -> dict[str, str]:
    out: dict[str, str] = {}
    for key, name in (("MODEL_PROVIDER", "provider"), ("MODEL_NAME", "model"),
                      ("MODEL_REASONING_LEVEL", "reasoning_level")):
        value = await runtime_settings.get_value(key, "")
        if value:
            out[name] = value
    return out


async def resolve_model_config(
    *,
    job_override: dict[str, Any] | None = None,
    step: str | None = None,
) -> dict[str, Any]:
    """Resolve provider/model/reasoning level: job > step > workspace > env.

    Unknown provider with a requested reasoning level rejects; we never guess
    a vendor's parameter name.
    """
    job_override = dict(job_override or {})
    level = job_override.get("reasoning_level")
    if level is not None and level not in REASONING_LEVELS:
        return {"ok": False, "error": "invalid_reasoning_level", "allowed": list(REASONING_LEVELS)}

    merged: dict[str, Any] = {}
    for source in (await _workspace_config(), await _step_config(step) if step else {}, job_override):
        for k, v in source.items():
            if v:
                merged[k] = v
    merged_level = merged.get("reasoning_level")
    if merged_level is not None and merged_level not in REASONING_LEVELS:
        return {"ok": False, "error": "invalid_reasoning_level", "allowed": list(REASONING_LEVELS),
                "source": "workspace_or_step"}
    provider = str(merged.get("provider") or active_provider())
    try:
        model = str(merged.get("model") or active_model(provider) or "")
    except ValueError:
        model = str(merged.get("model") or "")
    reasoning_level = merged.get("reasoning_level") or None

    reasoning_param = None
    if reasoning_level:
        reasoning_param = REASONING_PARAMS.get(provider)
        if reasoning_param is None:
            return {"ok": False, "error": "unknown_provider_reasoning_param",
                    "provider": provider,
                    "known_providers": sorted(REASONING_PARAMS)}
    return {"ok": True, "provider": provider, "model": model,
            "reasoning_level": reasoning_level, "reasoning_param": reasoning_param,
            "resolution_order": ["job", "step", "workspace", "env"]}


def reasoning_request_body(provider: str, reasoning_level: str) -> dict[str, Any] | None:
    """Vendor-shaped reasoning payload for a request body, or None if unknown.

    OpenRouter: {"reasoning": {"effort": level}}; OpenAI-compatible:
    {"reasoning_effort": level}; Anthropic manual mode needs a token budget,
    which we do not invent - caller must supply it explicitly.
    """
    if provider in ("openrouter",):
        return {"reasoning": {"effort": reasoning_level}}
    if provider in ("openai", "openai-compatible"):
        return {"reasoning_effort": reasoning_level}
    return None
