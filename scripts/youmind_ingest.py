"""Deterministic, provenance-first importer for upstream prompt libraries.

This compiler never publishes unknown-license material. Repositories must be
cloned beneath --source-root using their repository name (for example
`awesome-nano-banana-pro-prompts`). Verified sources are normalized into an
ICM-friendly card manifest; unknown or unsupported licenses are quarantined.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SUPPORTED_LICENSES = {
    "mit": "MIT",
    "cc by 4.0": "CC-BY-4.0",
    "creative commons attribution 4.0": "CC-BY-4.0",
    "apache license": "Apache-2.0",
}
SKIP_NAMES = {"readme.md", "license", "license.md", "contributing.md", "code_of_conduct.md"}
CANDIDATE_SUFFIXES = {".md", ".txt"}


@dataclass(frozen=True)
class Candidate:
    repo: str
    source_path: str
    title: str
    prompt: str
    license: str
    content_hash: str


def content_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def detect_license(repo_dir: Path) -> str | None:
    for name in ("LICENSE", "LICENSE.md", "license", "license.md"):
        path = repo_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for marker, canonical in SUPPORTED_LICENSES.items():
            if marker in text:
                return canonical
    return None


def title_from_path(path: Path) -> str:
    value = re.sub(r"[_-]+", " ", path.stem).strip()
    return value.title() or "Untitled Prompt"


def iter_candidates(repo: str, repo_dir: Path, license_name: str) -> Iterable[Candidate]:
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in CANDIDATE_SUFFIXES:
            continue
        if path.name.lower() in SKIP_NAMES or any(part.startswith(".") for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if len(text) < 20:
            continue
        digest = content_hash(text)
        yield Candidate(
            repo=repo,
            source_path=path.relative_to(repo_dir).as_posix(),
            title=title_from_path(path),
            prompt=text,
            license=license_name,
            content_hash=digest,
        )


def compile_registry(registry_path: Path, source_root: Path, output_root: Path) -> dict:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    cards: list[dict] = []
    quarantine: list[dict] = []
    seen_hashes: set[str] = set()

    for source in registry["repositories"]:
        repo = source["repo"]
        repo_name = repo.rsplit("/", 1)[-1]
        repo_dir = source_root / repo_name
        if not repo_dir.exists():
            quarantine.append({"repo": repo, "reason": "source-not-present"})
            continue

        detected = detect_license(repo_dir)
        declared = source.get("license") if source.get("license_status") == "verified" else None
        license_name = declared or detected
        if not license_name:
            quarantine.append({"repo": repo, "reason": "license-unverified"})
            continue

        for candidate in iter_candidates(repo, repo_dir, license_name):
            if candidate.content_hash in seen_hashes:
                continue
            seen_hashes.add(candidate.content_hash)
            cards.append({
                "id": f"upstream-{candidate.content_hash[:16]}",
                "title": candidate.title,
                "prompt": candidate.prompt,
                "category": "Unclassified",
                "subcategory": "Upstream",
                "tags": [],
                "source": {
                    "repo": candidate.repo,
                    "path": candidate.source_path,
                    "license": candidate.license,
                    "license_verified": True,
                    "content_hash": candidate.content_hash,
                },
                "icm_path": f"library/imported/{repo_name}/{candidate.content_hash[:16]}",
            })

    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "source": registry.get("source"),
        "cards": cards,
        "quarantine": quarantine,
        "counts": {"cards": len(cards), "quarantined_repositories": len(quarantine)},
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("sources/youmind-openlab.json"))
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("library/imported/youmind"))
    args = parser.parse_args()
    result = compile_registry(args.registry, args.source_root, args.output_root)
    print(json.dumps(result["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
