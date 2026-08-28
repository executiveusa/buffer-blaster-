"""Social publishing boundary.

TryPost is the default V1 publisher, but the application only depends on the
small normalized contract in this module. Public publishing always requires an
explicit human approval receipt.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx


@dataclass(slots=True)
class PublishRequest:
    content: str
    platforms: list[dict[str, Any]]
    scheduled_at: str
    approved: bool
    media_urls: list[str] = field(default_factory=list)
    label_ids: list[str] = field(default_factory=list)


class TryPostPublisher:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("TRYPOST_URL", "")).rstrip("/")
        self.token = token or os.getenv("TRYPOST_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def list_accounts(self) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "trypost_not_configured", "accounts": []}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/api/social-accounts", headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return {"ok": True, "provider": "trypost", "accounts": data}

    async def schedule(self, request: PublishRequest) -> dict[str, Any]:
        if not request.approved:
            return {"ok": False, "error": "human_approval_required"}
        if not request.scheduled_at:
            return {"ok": False, "error": "scheduled_at_required"}
        if not request.platforms:
            return {"ok": False, "error": "platform_required"}
        if not self.configured:
            return {"ok": False, "error": "trypost_not_configured"}

        payload: dict[str, Any] = {
            "content": request.content,
            "platforms": request.platforms,
            "scheduled_at": request.scheduled_at,
        }
        if request.label_ids:
            payload["label_ids"] = request.label_ids

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/posts",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        post_id = data.get("id") if isinstance(data, dict) else None
        if request.media_urls and post_id:
            for url in request.media_urls:
                media_response = await client_post_media_from_url(
                    self.base_url,
                    self._headers(),
                    str(post_id),
                    url,
                )
                if not media_response.get("ok"):
                    return {
                        "ok": False,
                        "error": "media_attach_failed",
                        "post": data,
                        "detail": media_response,
                    }

        return {
            "ok": True,
            "provider": "trypost",
            "post": data,
            "receipt": {
                "external_id": post_id,
                "scheduled_at": request.scheduled_at,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
        }


async def client_post_media_from_url(
    base_url: str,
    headers: dict[str, str],
    post_id: str,
    url: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{base_url}/api/posts/{post_id}/media/from-url",
            headers=headers,
            json={"url": url},
        )
        if response.is_error:
            return {"ok": False, "status": response.status_code, "body": response.text[:500]}
        return {"ok": True, "data": response.json()}


def get_publisher() -> TryPostPublisher:
    """Return the configured publisher without leaking credentials."""
    return TryPostPublisher()
