"""Build a deterministic, portable ICM Agent Pack ZIP from an imported card library.

The exporter is intentionally filesystem-first. It validates that every exported
card has verified license/provenance metadata, writes global routing contracts,
and produces byte-for-byte deterministic ZIP output for the same input tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

AGENTS_MD = """# Creator Agent Pack

This pack is portable reference context for AI agents.

## Operating rules
1. Read `CONTEXT.md` first.
2. Route to the smallest matching category/card context; do not load the entire library.
3. Treat `cards/**/card.json` and `cards/**/CONTEXT.md` as read-only factory context.
4. Put run-specific work in `output/`; never overwrite source cards.
5. Preserve source attribution and license metadata when adapting or redistributing cards.
6. Human review is required before publishing or sending generated work externally.
"""

ROOT_CONTEXT_MD = """# Context Router

## Goal
Find the smallest relevant creative recipe for the current creator task.

## Routing
- Image generation, photography, graphics, thumbnails → `cards/images/`
- Video, reels, motion, trailers → `cards/video/`
- Agent skills and reusable automation → `cards/agents/`
- Unknown/unclassified tasks → `cards/unclassified/`

## Context discipline
Read the target card's `CONTEXT.md` and `card.json` only after routing. Do not put the full manifest into model context. `manifest.json` is an index for search and software, not a prompt.

## Working artifacts
Write generated or adapted work to `output/`. The `output/` directory is the mutable product layer; the card library is stable reference context.
"""

README_MD = """# Portable Creator Agent Pack

This ZIP is an Interpretable Context Methodology (ICM) package generated from a provenance-checked creator card library.

Start with `AGENTS.md`, then `CONTEXT.md`. Software integrations should use `manifest.json` for indexing and load individual card folders on demand.
"""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_manifest(manifest: dict) -> None:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise ValueError("manifest.cards must be a list")
    for card in cards:
        source = card.get("source", {})
        if source.get("license_verified") is not True:
            raise ValueError(f"card {card.get('id', '<unknown>')} has unverified license")
        for field in ("repo", "path", "license", "content_hash"):
            if not source.get(field):
                raise ValueError(f"card {card.get('id', '<unknown>')} missing source.{field}")
        icm_path = card.get("icm_path")
        if not icm_path or ".." in PurePosixPath(icm_path).parts:
            raise ValueError(f"card {card.get('id', '<unknown>')} has unsafe icm_path")


def _zip_write(zf: zipfile.ZipFile, arcname: str, content: bytes) -> None:
    info = zipfile.ZipInfo(arcname, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, content)


def build_bundle(library_root: Path, output_zip: Path) -> dict:
    manifest_path = library_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)

    required_files: list[tuple[str, bytes]] = [
        ("AGENTS.md", AGENTS_MD.encode("utf-8")),
        ("CONTEXT.md", ROOT_CONTEXT_MD.encode("utf-8")),
        ("README.md", README_MD.encode("utf-8")),
        ("manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")),
        ("output/.gitkeep", b""),
    ]

    exported_cards = 0
    for card in sorted(manifest["cards"], key=lambda item: item["id"]):
        card_dir = library_root / card["icm_path"]
        for filename in ("card.json", "CONTEXT.md"):
            path = card_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"missing card artifact: {path}")
            required_files.append((f"{card['icm_path']}/{filename}", path.read_bytes()))
        exported_cards += 1

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w") as zf:
        for arcname, content in sorted(required_files, key=lambda item: item[0]):
            _zip_write(zf, arcname, content)

    bundle_bytes = output_zip.read_bytes()
    receipt = {
        "schema_version": 1,
        "cards": exported_cards,
        "files": len(required_files),
        "sha256": sha256_bytes(bundle_bytes),
        "size_bytes": len(bundle_bytes),
        "output": output_zip.name,
    }
    receipt_path = output_zip.with_suffix(output_zip.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library-root", type=Path, default=Path("library/imported/youmind"))
    parser.add_argument("--output", type=Path, default=Path("dist/buffer-blaster-a2a-library.zip"))
    args = parser.parse_args()
    receipt = build_bundle(args.library_root, args.output)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
