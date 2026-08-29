"""Social publishing boundary.

Buffer Blaster / Social Studio is a standalone application. Public publishing
is an optional downstream integration and always requires explicit human
approval. Core campaign planning, UGC prompt compilation, media generation,
scoring, and review do not depend on external publishing infrastructure.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass(slots=True)
class PublishRequest:
    content: str
    platforms: list[dict[str, Any]]
    scheduled_at: str
    approved: bool
    media_urls: list[str] = field(default_factory=list)
    label_ids: list[str] = field(default_factory=list)


class PublishingProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    def status(self) -> dict[str, Any]: ...

    async def list_accounts(self) -> dict[str, Any]: ...

    async def schedule(self, request: PublishRequest) -> dict[str, Any]: ...


class DisabledPublishingProvider:
    """Default provider when no downstream publishing integration is attached."""

    @property
    def configured(self) -> bool:
        return False

    def status(self) -> dict[str, Any]:
        return {
            "enabled": False,
            "provider": None,
            "configured": False,
            "required_for_core": False,
        }

    async def list_accounts(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": "publishing_integration_disabled",
            "accounts": [],
        }

    async def schedule(self, request: PublishRequest) -> dict[str, Any]:
        if not request.approved:
            return {"ok": False, "error": "human_approval_required"}
        return {
            "ok": False,
            "error": "publishing_integration_disabled",
            "message": "No external publishing provider is configured.",
        }


def get_publisher() -> PublishingProvider:
    """Return the configured publishing provider (disabled by default in core)."""
    return DisabledPublishingProvider()
