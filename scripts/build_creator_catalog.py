#!/usr/bin/env python3
"""Compile provenance-verified imported cards into compact search and full-card catalogs.

The compiler never imports unverified cards. It keeps browser/search payloads compact
while preserving full prompts and provenance in a separate server artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SEARCH_FIELDS = (
    "id", "slug", "title", "description", "category", "subcategory", "media_type",
    "tags", "model_hints", "required_inputs", "requires_reference", "quality_score", "source",
)


def load_verified_cards(root: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for path in sorted(root.rglob("card.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        source = card.get("source") or {}
        if source.get("license_verified") is not True:
            continue
        prompt = str(card.get("prompt") or "").strip()
        if not prompt:
            continue
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if prompt_hash in seen_hashes:
            continue
        seen_hashes.add(prompt_hash)
        card.setdefault("prompt_content_hash", prompt_hash)
        cards.append(card)
    return sorted(cards, key=lambda item: str(item.get("id", "")))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="library/imported/youmind")
    parser.add_argument("--output", default="library/compiled")
    args = parser.parse_args()

    root = Path(args.input)
    output = Path(args.output)
    cards = load_verified_cards(root) if root.exists() else []
    search = [{key: card.get(key) for key in SEARCH_FIELDS if key in card} for card in cards]

    write_json(output / "search-catalog.json", {"schema_version": 1, "count": len(search), "cards": search})
    write_json(output / "full-cards.json", {"schema_version": 1, "count": len(cards), "cards": cards})
    digest = hashlib.sha256((output / "full-cards.json").read_bytes()).hexdigest()
    write_json(output / "manifest.json", {"schema_version": 1, "count": len(cards), "sha256": digest, "license_gate": "verified-only"})
    print(f"compiled {len(cards)} verified cards -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
