"""Server-owned multi-gateway configuration for Buffer Blaster media generation."""
from __future__ import annotations

import json
import os
from typing import Any

from .universal_media_gateway import UniversalVideoGatewayProvider


def _load_profiles() -> list[dict[str, Any]]:
    raw = (os.getenv("GENERATION_GATEWAYS_JSON") or "").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    profiles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        api_key_env = str(item.get("api_key_env") or "").strip()
        base_url = str(item.get("base_url") or "").strip()
        text_model = str(item.get("text_model") or "").strip()
        image_model = str(item.get("image_model") or "").strip()
        if not api_key_env or not base_url or not (text_model or image_model):
            continue
        seen.add(name)
        profiles.append(dict(item))
    return profiles


def configured_gateway_providers() -> dict[str, UniversalVideoGatewayProvider]:
    """Return configured named gateways without exposing inline secrets."""
    providers: dict[str, UniversalVideoGatewayProvider] = {}
    for profile in _load_profiles():
        provider = UniversalVideoGatewayProvider(profile=profile)
        if provider.configured:
            providers[provider.name] = provider
    return providers


def gateway_catalog() -> list[dict[str, Any]]:
    """Return safe provider/model metadata for UI, MCP, and routing surfaces."""
    items: list[dict[str, Any]] = []
    for provider in configured_gateway_providers().values():
        caps = provider.capabilities()
        items.append({
            "provider": provider.name,
            "models": provider.models(),
            "deployment": caps.deployment,
            "commercial_use_status": caps.commercial_use_status,
            "estimated_cost_cents": caps.estimated_cost_cents,
            "estimated_latency_seconds": caps.estimated_latency_seconds,
            "health": caps.health,
        })
    return sorted(items, key=lambda item: item["provider"])
