"""In-memory demo data — what the dashboard shows when no Supabase is wired.

Two seeded clients across two niches, with content units tagged by their
isolated schema name. This is the data the owners see in the demo.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone


def _schema(slug: str) -> str:
    return f"schema_{re.sub(r'[^a-z0-9]', '_', slug.lower())}"


_CLIENTS = [
    {
        "id": "demo-cella",
        "slug": "cella-coffee",
        "name": "Cella Coffee Roasters",
        "niche": "food-beverage",
        "shopify_url": "https://cella-coffee.myshopify.com",
        "schema": _schema("cella-coffee"),
        "created_at": "2026-06-14T09:00:00Z",
        "status": "active",
        "posts_scheduled": 47,
        "avg_score": 84.2,
    },
    {
        "id": "demo-lumen",
        "slug": "lumen-skincare",
        "name": "Lumen Skincare",
        "niche": "beauty-skincare",
        "shopify_url": "https://lumen-skincare.myshopify.com",
        "schema": _schema("lumen-skincare"),
        "created_at": "2026-06-20T09:00:00Z",
        "status": "active",
        "posts_scheduled": 31,
        "avg_score": 86.7,
    },
]


def _unit(client_slug: str, platform: str, hook: str, score: int, status: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "client_slug": client_slug,
        "schema": _schema(client_slug),
        "platform": platform,
        "hook": hook,
        "caption": f"{hook} — Swipe to see how we made it.",
        "raw_score": score,
        "score_breakdown": {
            "hook_strength": round(score * 0.25 / 0.25),
            "platform_fit": round(score * 0.20 / 0.25),
            "niche_relevance": round(score * 0.20 / 0.25),
            "trend_alignment": round(score * 0.15 / 0.25),
            "visual_quality": round(score * 0.10 / 0.25),
            "audience_match": round(score * 0.10 / 0.25),
        },
        "status": status,
    }


_UNITS = [
    _unit("cella-coffee", "tiktok", "We roasted 1,000 beans and only 12 made the cut.", 91, "approved"),
    _unit("cella-coffee", "instagram", "The pour that took our barista 4 years to nail.", 85, "approved"),
    _unit("cella-coffee", "pinterest", "Morning ritual: 3 minutes, zero rush.", 78, "pending"),
    _unit("lumen-skincare", "instagram", "She used our serum for 30 days. Here's day 14.", 88, "approved"),
    _unit("lumen-skincare", "tiktok", "The ingredient dermatologists won't name on camera.", 93, "pending"),
    _unit("lumen-skincare", "youtube", "Why your $80 cream isn't doing what you think.", 74, "rejected"),
]


_PIPELINE_RUNS: dict[str, dict] = {}


def list_clients() -> list[dict]:
    return [dict(c) for c in _CLIENTS]


def get_client(slug: str) -> dict | None:
    for c in _CLIENTS:
        if c["slug"] == slug:
            return dict(c)
    return None


def schema_for(slug: str) -> str | None:
    c = get_client(slug)
    return c["schema"] if c else None


def add_client(*, name: str, niche: str, slug: str, schema: str) -> dict:
    client = {
        "id": f"demo-{slug}",
        "slug": slug,
        "name": name,
        "niche": niche,
        "shopify_url": "",
        "schema": schema,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "posts_scheduled": 0,
        "avg_score": 0.0,
    }
    _CLIENTS.append(client)
    return client


def content_for(slug: str) -> list[dict]:
    return [dict(u) for u in _UNITS if u["client_slug"] == slug]


def approve(unit_id: str) -> bool:
    for u in _UNITS:
        if u["id"] == unit_id:
            u["status"] = "approved"
            return True
    return False


def reject(unit_id: str) -> bool:
    for u in _UNITS:
        if u["id"] == unit_id:
            u["status"] = "rejected"
            return True
    return False


def pending_approvals() -> int:
    return sum(1 for u in _UNITS if u["status"] == "pending")


def posts_this_week() -> int:
    return sum(1 for u in _UNITS if u["status"] == "approved")


def pipeline_running() -> bool:
    return any(r["status"] == "running" for r in _PIPELINE_RUNS.values())


def start_pipeline(slug: str) -> dict:
    run = {"id": str(uuid.uuid4())[:8], "client": slug, "status": "running",
           "started_at": datetime.now(timezone.utc).isoformat()}
    _PIPELINE_RUNS[slug] = run
    return run


def pipeline_status(slug: str) -> dict:
    return _PIPELINE_RUNS.get(slug, {"client": slug, "status": "idle"})
