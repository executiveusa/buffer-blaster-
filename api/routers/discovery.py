"""Public creator discovery API.

This router exposes only curated card metadata and recipes. It does not expose
private client data, internal agent names, credentials, or admin operations.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.discovery import discover, get_card

router = APIRouter(prefix="/v1", tags=["creator-discovery"])


class DiscoverRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=3, ge=1, le=12)


@router.post("/discover")
async def discover_cards(payload: DiscoverRequest) -> dict:
    cards = discover(payload.intent, payload.limit)
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
    return {"card": card}
