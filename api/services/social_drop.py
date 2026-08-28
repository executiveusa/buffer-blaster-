"""Canonical social-drop contract shared by UI, agents, MCP, CLI, and publishers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_FORMATS = {
    "instagram": {"post", "reel", "story", "carousel"},
    "instagram-facebook": {"post", "reel", "story", "carousel"},
    "facebook": {"post", "reel", "story", "carousel"},
    "linkedin": {"post", "carousel"},
    "linkedin-page": {"post", "carousel"},
    "x": {"post"},
    "tiktok": {"reel"},
    "youtube": {"reel"},
    "threads": {"post"},
    "pinterest": {"post", "carousel"},
    "bluesky": {"post"},
    "mastodon": {"post"},
    "telegram": {"post"},
    "discord": {"post"},
}


@dataclass(slots=True)
class SocialDrop:
    id: str
    content: str
    format: str
    platforms: list[dict[str, Any]]
    scheduled_at: str | None = None
    media_urls: list[str] = field(default_factory=list)
    approved: bool = False
    campaign_id: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id.strip():
            errors.append("id_required")
        if not self.content.strip():
            errors.append("content_required")
        if not self.platforms:
            errors.append("platform_required")
        for platform in self.platforms:
            name = str(platform.get("platform") or platform.get("type") or "").lower()
            if name and name in SUPPORTED_FORMATS and self.format not in SUPPORTED_FORMATS[name]:
                errors.append(f"{self.format}_not_supported_on_{name}")
            if not platform.get("social_account_id"):
                errors.append("social_account_id_required")
        return sorted(set(errors))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def platform_payload(drop: SocialDrop) -> list[dict[str, Any]]:
    """Strip local-only keys before sending platform objects to TryPost."""
    out: list[dict[str, Any]] = []
    for item in drop.platforms:
        payload = {
            "social_account_id": item["social_account_id"],
            "content_type": item.get("content_type") or drop.format,
        }
        if item.get("meta"):
            payload["meta"] = item["meta"]
        out.append(payload)
    return out
