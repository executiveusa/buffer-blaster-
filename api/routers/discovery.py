"""Public creator discovery API.

Public responses intentionally expose only creator-safe card fields. Internal
repository paths, content hashes, engine names, and ICM implementation paths
remain server-side for provenance and export compilation.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.discovery import discover, get_card

router = APIRouter(prefix="/v1", tags=["creator-discovery"])


class DiscoverRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=3, ge=1, le=12)


def _public_card(card: dict[str, Any]) -> dict[str, Any]:
    """Return the public DTO without internal architecture/provenance paths."""
    source = card.get("source", {})
    return {
        "id": card.get("id"),
        "slug": card.get("slug"),
        "title": card.get("title"),
        "description": card.get("description"),
        "category": card.get("category"),
        "subcategory": card.get("subcategory"),
        "media_type": card.get("media_type"),
        "prompt": card.get("prompt"),
        "tags": card.get("tags", []),
        "model_hints": card.get("model_hints", []),
        "preview_assets": card.get("preview_assets", []),
        "required_inputs": card.get("required_inputs", []),
        "requires_reference": card.get("requires_reference", False),
        "quality_score": card.get("quality_score"),
        "source": {
            "attribution": "Curated recipe",
            "license": source.get("license", "unknown"),
            "license_verified": bool(source.get("license_verified", False)),
        },
    }


@router.post("/discover")
async def discover_cards(payload: DiscoverRequest) -> dict:
    cards = [_public_card(card) for card in discover(payload.intent, payload.limit)]
    return {
        "intent": payload.intent,
        "count": len(cards),
        "cards": cards,
    }


@router.get("/cards/{card_id}")
async def card_detail(card_id: str) -> dict:
    card = get_card(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="card not found")
    return {"card": _public_card(card)}
