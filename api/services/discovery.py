"""Creator card discovery service.

V1 deliberately uses deterministic lexical/tag ranking. This keeps the first
sellable slice inspectable and testable. Embeddings can be added later behind
the same contract if measured retrieval quality requires them.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "creator_cards.json"
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


@lru_cache(maxsize=1)
def load_cards() -> list[dict[str, Any]]:
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        cards = json.load(handle)
    if not isinstance(cards, list):
        raise ValueError("creator_cards.json must contain a list")
    return cards


def _score(card: dict[str, Any], intent_tokens: set[str]) -> int:
    if not intent_tokens:
        return int(card.get("quality_score", 0))

    title = _tokens(str(card.get("title", "")))
    description = _tokens(str(card.get("description", "")))
    tags = {str(tag).lower() for tag in card.get("tags", [])}
    category = _tokens(f"{card.get('category', '')} {card.get('subcategory', '')}")

    score = 0
    score += 8 * len(intent_tokens & title)
    score += 5 * len(intent_tokens & tags)
    score += 3 * len(intent_tokens & category)
    score += 2 * len(intent_tokens & description)
    score += int(card.get("quality_score", 0)) // 10
    return score


def discover(intent: str, limit: int = 3) -> list[dict[str, Any]]:
    """Return the best matching cards for a creator intent.

    Deterministic tie-breaking keeps UI/API/test behavior stable.
    """
    bounded_limit = max(1, min(limit, 12))
    intent_tokens = _tokens(intent)
    ranked = sorted(
        load_cards(),
        key=lambda card: (
            -_score(card, intent_tokens),
            -int(card.get("quality_score", 0)),
            str(card.get("id", "")),
        ),
    )
    return ranked[:bounded_limit]


def get_card(card_id: str) -> dict[str, Any] | None:
    for card in load_cards():
        if card.get("id") == card_id or card.get("slug") == card_id:
            return card
    return None
