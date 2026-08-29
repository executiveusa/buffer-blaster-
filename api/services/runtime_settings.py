"""Small Redis-backed runtime settings store for non-secret operator settings.

Secrets remain environment/secret-store managed. This store exists only for
safe settings that an operator can legitimately change from the UI while the
API is running. Redis AOF in the self-host stack makes these values durable
across API restarts and visible to all workers.
"""
from __future__ import annotations

import os
from typing import Any

import redis.asyncio as redis


_ALLOWED = {"ACTIVE_LLM_PROVIDER", "AGENT_MAX_CHILDREN"}
_HASH_KEY = "buffer_blaster:runtime_settings:v1"


def allowed_key(key: str) -> bool:
    return key in _ALLOWED


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


async def get_value(key: str, default: str = "") -> str:
    if not allowed_key(key):
        return default
    url = _redis_url()
    if url:
        client = redis.from_url(url, decode_responses=True)
        try:
            value = await client.hget(_HASH_KEY, key)
            if value is not None:
                return str(value)
        except redis.RedisError:
            pass
        finally:
            await client.aclose()
    return os.getenv(key, default)


async def set_value(key: str, value: str) -> dict[str, Any]:
    if not allowed_key(key):
        return {"ok": False, "error": "setting_not_runtime_editable", "env": key}

    clean = value.strip()
    if key == "AGENT_MAX_CHILDREN":
        try:
            count = int(clean)
        except ValueError:
            return {"ok": False, "error": "invalid_integer", "env": key}
        if count < 1 or count > 100:
            return {"ok": False, "error": "out_of_range", "env": key, "minimum": 1, "maximum": 100}
        clean = str(count)
    elif key == "ACTIVE_LLM_PROVIDER" and clean not in {"anthropic", "openai", "google", "ollama"}:
        return {
            "ok": False,
            "error": "unsupported_llm_provider",
            "env": key,
            "allowed": ["anthropic", "openai", "google", "ollama"],
        }

    url = _redis_url()
    if not url:
        return {
            "ok": False,
            "error": "runtime_store_unavailable",
            "env": key,
            "message": "REDIS_URL is required for durable runtime settings.",
        }

    client = redis.from_url(url, decode_responses=True)
    try:
        await client.hset(_HASH_KEY, key, clean)
    except redis.RedisError as exc:
        return {"ok": False, "error": "runtime_store_write_failed", "env": key, "detail": type(exc).__name__}
    finally:
        await client.aclose()

    return {"ok": True, "env": key, "value": clean, "durable": True, "store": "redis"}
