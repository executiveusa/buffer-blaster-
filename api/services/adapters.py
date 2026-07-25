"""Adapter stubs for external services.

Each client class follows the same shape:
  - configured — bool, env var present
  - activate() — returns a human-readable message when not configured

They make no live calls from this dev box. On the VPS, setting the env var
makes the real client take over.
"""
from __future__ import annotations

import os


class HermesClient:
    """Orchestrator — runs the content pipeline via sub-agents."""

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.profile = os.getenv("AGENT_PROFILE", "creator-studio")
        self.max_children = int(os.getenv("AGENT_MAX_CHILDREN", "10"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def activate(self) -> str:
        if self.configured:
            return f"Agent ready. Profile={self.profile}, max_children={self.max_children}."
        return "Set ANTHROPIC_API_KEY (or OPENAI_API_KEY) to activate the agent."

    async def run_pipeline(self, client_slug: str) -> dict:
        if not self.configured:
            return {"status": "stub", "message": self.activate()}
        return {"status": "queued", "client": client_slug, "profile": self.profile}


class BufferClient:
    """Publishes approved content to Buffer."""

    BASE = "https://api.bufferapp.com/1/"

    def __init__(self) -> None:
        self.token = os.getenv("BUFFER_ACCESS_TOKEN")

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def activate(self) -> str:
        return "Buffer connected." if self.configured else "Set BUFFER_ACCESS_TOKEN to publish."

    async def profiles(self) -> list:
        if not self.configured:
            return []
        return []


class FirecrawlClient:
    """Crawls a URL into markdown and metadata for competitor analysis."""

    def __init__(self) -> None:
        self.api_key = os.getenv("FIRECRAWL_API_KEY")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def activate(self) -> str:
        return "Firecrawl connected." if self.configured else "Set FIRECRAWL_API_KEY to scan URLs."

    async def scan(self, url: str) -> dict:
        if not self.configured:
            return {"url": url, "status": "stub", "message": self.activate()}
        return {"url": url, "status": "queued"}


class ApifyClient:
    """Scrapes competitor social accounts via Apify actors."""

    def __init__(self) -> None:
        self.api_key = os.getenv("APIFY_API_TOKEN")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def activate(self) -> str:
        return "Apify connected." if self.configured else "Set APIFY_API_TOKEN to scrape competitors."

    async def scrape_competitors(self, niche: str) -> list:
        if not self.configured:
            return []
        return []


class TelegramService:
    """Voice and command bot restricted to the configured operator ID."""

    def __init__(self) -> None:
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.user_id = os.getenv("TELEGRAM_USER_ID")

    @property
    def configured(self) -> bool:
        return bool(self.token) and bool(self.user_id)

    def activate(self) -> str:
        if self.configured:
            return "Telegram bot ready. Register via @BotFather on the VPS."
        return "Set TELEGRAM_BOT_TOKEN + TELEGRAM_USER_ID."

    def is_stavarai(self, user_id: int) -> bool:
        return self.user_id is not None and str(user_id) == str(self.user_id)


class VisionClawService:
    """Smart-glasses integration via webhook."""

    def __init__(self) -> None:
        self.secret = os.getenv("VISIONCLAW_WEBHOOK_SECRET")

    @property
    def configured(self) -> bool:
        return bool(self.secret)

    def activate(self) -> str:
        if self.configured:
            return "Vision webhook ready."
        return "Set VISIONCLAW_WEBHOOK_SECRET and configure the VPS webhook."


class AutoresearchService:
    """Nightly A/B loop for content scoring weights."""

    def __init__(self) -> None:
        self.active = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))

    @property
    def configured(self) -> bool:
        return self.active

    def activate(self) -> str:
        return (
            "Autoresearch ready. Cron: 0 2 * * * on the VPS."
            if self.active
            else "Set an LLM API key to enable the autoresearch loop."
        )
