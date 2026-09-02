"""Optional downstream social publishing boundary for Buffer Blaster.

Core research, planning, UGC production, scoring, and review do not depend on an
external publisher. Publishing always requires explicit human approval. Buffer
can be selected as a downstream distribution provider without moving provider
credentials or authority into the browser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


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


class BufferPublishingProvider:
    """Buffer GraphQL adapter. `social_account_id` maps to a Buffer channel ID."""

    endpoint = "https://api.buffer.com"

    @property
    def configured(self) -> bool:
        return bool(os.getenv("BUFFER_API_KEY", "").strip())

    def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "provider": "buffer",
            "configured": self.configured,
            "required_for_core": False,
        }

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        token = os.getenv("BUFFER_API_KEY", "").strip()
        if not token:
            return {"ok": False, "error": "buffer_not_configured"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": variables or {}},
                )
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "buffer_request_failed", "detail": type(exc).__name__}
        if response.status_code == 401:
            return {"ok": False, "error": "buffer_unauthorized"}
        if not response.is_success:
            return {"ok": False, "error": "buffer_http_error", "status": response.status_code}
        try:
            payload = response.json()
        except ValueError:
            return {"ok": False, "error": "buffer_invalid_response"}
        if payload.get("errors"):
            return {"ok": False, "error": "buffer_graphql_error", "errors": payload["errors"]}
        return {"ok": True, "data": payload.get("data") or {}}

    async def _organization_id(self) -> str | None:
        configured = os.getenv("BUFFER_ORGANIZATION_ID", "").strip()
        if configured:
            return configured
        result = await self._graphql(
            "query BufferOrganizations { account { organizations { id name } } }"
        )
        if not result.get("ok"):
            return None
        organizations = result.get("data", {}).get("account", {}).get("organizations") or []
        return str(organizations[0].get("id")) if organizations else None

    async def list_accounts(self) -> dict[str, Any]:
        organization_id = await self._organization_id()
        if not organization_id:
            return {"ok": False, "error": "buffer_organization_not_found", "accounts": []}
        result = await self._graphql(
            """
            query BufferChannels($organizationId: OrganizationId!) {
              channels(input: { organizationId: $organizationId }) {
                id
                name
                displayName
                service
                isQueuePaused
              }
            }
            """,
            {"organizationId": organization_id},
        )
        if not result.get("ok"):
            return {**result, "accounts": []}
        channels = result.get("data", {}).get("channels") or []
        return {
            "ok": True,
            "provider": "buffer",
            "organization_id": organization_id,
            "accounts": [
                {
                    "social_account_id": row.get("id"),
                    "name": row.get("displayName") or row.get("name"),
                    "platform": row.get("service"),
                    "queue_paused": bool(row.get("isQueuePaused")),
                }
                for row in channels
            ],
        }

    @staticmethod
    def _assets(media_urls: list[str]) -> list[dict[str, Any]]:
        assets: list[dict[str, Any]] = []
        for url in media_urls:
            clean = str(url).strip()
            if not clean:
                continue
            lower = clean.split("?", 1)[0].lower()
            if lower.endswith((".mp4", ".mov", ".m4v", ".webm")):
                assets.append({"video": {"url": clean}})
            else:
                assets.append({"image": {"url": clean}})
        return assets

    async def schedule(self, request: PublishRequest) -> dict[str, Any]:
        if not request.approved:
            return {"ok": False, "error": "human_approval_required"}
        if not self.configured:
            return {"ok": False, "error": "buffer_not_configured"}
        channel_ids = [str(item.get("social_account_id") or "").strip() for item in request.platforms]
        if not channel_ids or any(not channel_id for channel_id in channel_ids):
            return {"ok": False, "error": "buffer_channel_id_required"}

        mutation = """
        mutation BufferCreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess {
              post { id text status dueAt }
            }
            ... on MutationError { message }
          }
        }
        """
        assets = self._assets(request.media_urls)
        receipts: list[dict[str, Any]] = []
        for channel_id in channel_ids:
            post_input: dict[str, Any] = {
                "text": request.content,
                "channelId": channel_id,
                "schedulingType": "automatic",
                "mode": "customScheduled" if request.scheduled_at else "addToQueue",
                "aiAssisted": True,
                "assets": assets,
            }
            if request.scheduled_at:
                post_input["dueAt"] = request.scheduled_at
            result = await self._graphql(mutation, {"input": post_input})
            if not result.get("ok"):
                return {**result, "provider": "buffer", "receipts": receipts}
            action = result.get("data", {}).get("createPost") or {}
            if action.get("message"):
                return {
                    "ok": False,
                    "error": "buffer_post_rejected",
                    "message": action.get("message"),
                    "provider": "buffer",
                    "receipts": receipts,
                }
            post = action.get("post") or {}
            if not post.get("id"):
                return {"ok": False, "error": "buffer_post_missing_receipt", "provider": "buffer", "receipts": receipts}
            receipts.append(
                {
                    "provider": "buffer",
                    "external_post_id": post.get("id"),
                    "status": post.get("status"),
                    "scheduled_at": post.get("dueAt") or request.scheduled_at,
                    "channel_id": channel_id,
                }
            )
        return {"ok": True, "provider": "buffer", "receipts": receipts, "count": len(receipts)}


def get_publisher() -> PublishingProvider:
    """Return the optional configured publishing provider; disabled is the safe default."""
    provider = os.getenv("PUBLISHING_PROVIDER", "").strip().lower()
    if provider == "buffer":
        return BufferPublishingProvider()
    return DisabledPublishingProvider()
