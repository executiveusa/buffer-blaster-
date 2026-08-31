"""Provider registry for money-loop paid media adapters."""
from __future__ import annotations

from .meta_ads import MetaAdsProvider
from .tiktok_ads import TikTokAdsProvider

_PROVIDERS = {
    "meta": MetaAdsProvider(),
    "tiktok": TikTokAdsProvider(),
}


def get_ads_provider(name: str):
    key = (name or "").strip().lower()
    if key not in _PROVIDERS:
        raise KeyError(f"unknown_ads_provider:{key}")
    return _PROVIDERS[key]


def provider_statuses() -> list[dict]:
    return [provider.status() for provider in _PROVIDERS.values()]
