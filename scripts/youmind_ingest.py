"""Deterministic, provenance-first importer for upstream prompt libraries.

Verified upstream repositories are normalized into individual cards and an
ICM-friendly filesystem. Unknown-license material is quarantined. The importer
supports prompt-library READMEs that use numbered sections with Description and
Prompt blocks, while retaining the generic file adapter for skill/text repos.
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
HF_DATASET_CDN_BASE = "https://huggingface.co/datasets/GokuScraper/seedance-2-prompts-datasets/resolve/main"
README_PROMPT_RE = re.compile(
    r"^###\s+No\.\s*(?P<number>\d+)\s*:\s*(?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^###\s+No\.\s*\d+\s*:|\Z)",
    re.MULTILINE | re.DOTALL,
)
DESCRIPTION_RE = re.compile(r"^####\s+.*?Description\s*$\s*(?P<description>.*?)(?=^####\s+|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
PROMPT_RE = re.compile(r"^####\s+.*?Prompt\s*$\s*```[^\n]*\n(?P<prompt>.*?)\n```", re.MULTILINE | re.DOTALL | re.IGNORECASE)
TITLED_SECTION_RE = re.compile(
    r"^###\s+(?!No\.)(?P<title>.+?)\s*$"
    r"(?P<body>.*?)(?=^###\s+|^##\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)
BLOCKQUOTE_RE = re.compile(r"^>\s*(?P<description>.+?)\s*$", re.MULTILINE)
ATTRIBUTION_RE = re.compile(
    r"\*\*Author:\*\*\s*(?P<author>.*?)\s*\|\s*\*\*Source:\*\*\s*(?P<source>.*?)\s*\|\s*\*\*Published:\*\*\s*(?P<published>.*?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Candidate:
    repo: str
    source_path: str
    title: str
    description: str
    prompt: str
    license: str
    content_hash: str
    adapter: str
    tags: tuple = ()
    author: str = ""
    source_link: str = ""
    subcategory: str = ""
    featured: bool = False
    dataset_record: bool = False
    preview_url: str = ""


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


def clean_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[`*_>#]", "", value)
    return " ".join(value.split()).strip()


def iter_readme_prompt_candidates(repo: str, repo_dir: Path, license_name: str) -> Iterable[Candidate]:
    readme = repo_dir / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8", errors="ignore")
    for match in README_PROMPT_RE.finditer(text):
        body = match.group("body")
        prompt_match = PROMPT_RE.search(body)
        if not prompt_match:
            continue
        prompt = prompt_match.group("prompt").strip()
        if len(prompt) < 20:
            continue
        description_match = DESCRIPTION_RE.search(body)
        description = clean_markdown(description_match.group("description")) if description_match else ""
        digest = content_hash(prompt)
        yield Candidate(
            repo=repo,
            source_path=f"README.md#no-{match.group('number')}",
            title=clean_markdown(match.group("title")),
            description=description,
            prompt=prompt,
            license=license_name,
            content_hash=digest,
            adapter="numbered-readme",
        )


def _first_link(value: str) -> str:
    match = re.search(r"\((https?://[^)]+)\)", value)
    if match:
        return match.group(1)
    match = re.search(r"(https?://\S+)", value)
    return match.group(1) if match else ""


def iter_titled_readme_candidates(repo: str, repo_dir: Path, license_name: str) -> Iterable[Candidate]:
    """Parse `### Title` sections with Prompt blocks (e.g. awesome-list 'All Prompts' sections)."""
    readme = repo_dir / "README.md"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8", errors="ignore")
    for match in TITLED_SECTION_RE.finditer(text):
        body = match.group("body")
        prompt_match = PROMPT_RE.search(body)
        if not prompt_match:
            continue
        prompt = prompt_match.group("prompt").strip()
        if len(prompt) < 20:
            continue
        quote_match = BLOCKQUOTE_RE.search(body)
        description = clean_markdown(quote_match.group("description")) if quote_match else ""
        attribution = ATTRIBUTION_RE.search(body)
        author = clean_markdown(attribution.group("author")) if attribution else ""
        source_link = _first_link(attribution.group("source")) if attribution else ""
        digest = content_hash(prompt)
        yield Candidate(
            repo=repo,
            source_path=f"README.md#{re.sub(r'[^a-z0-9]+', '-', match.group('title').lower()).strip('-')}",
            title=clean_markdown(match.group("title")),
            description=description,
            prompt=prompt,
            license=license_name,
            content_hash=digest,
            adapter="titled-readme",
            author=author,
            source_link=source_link,
        )


def iter_jsonl_dataset_candidates(repo: str, repo_dir: Path, license_name: str) -> Iterable[Candidate]:
    """Parse a structured prompt dataset (metadata.jsonl) into one candidate per record.

    Dataset records join the manifest and compiled catalogs but do not explode
    into per-card ICM folders; the JSONL itself remains the benchmark artifact.
    """
    dataset = repo_dir / "metadata.jsonl"
    if not dataset.exists():
        return
    for line_number, line in enumerate(dataset.read_text(encoding="utf-8-sig", errors="ignore").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        en = (record.get("i18n") or {}).get("en") or {}
        prompt = str(en.get("p") or record.get("raw_p") or "").strip()
        if len(prompt) < 20:
            continue
        title = str(en.get("t") or record.get("slug") or record.get("id") or f"record-{line_number}").strip()
        tags = tuple(str(tag) for tag in (en.get("tags") or []) if str(tag).strip())
        file_name = str(record.get("file_name") or "").lstrip("./")
        preview_url = f"{HF_DATASET_CDN_BASE}/{file_name}" if file_name else ""
        yield Candidate(
            repo=repo,
            source_path=f"metadata.jsonl#{record.get('id') or line_number}",
            title=title,
            description="",
            prompt=prompt,
            license=license_name,
            content_hash=content_hash(prompt),
            adapter="jsonl-dataset",
            tags=tags,
            source_link=str(record.get("sourceLink") or ""),
            subcategory=f"Seedance 2 \u00b7 {record.get('category')}" if record.get("category") else "Seedance 2",
            featured=bool(record.get("is_featured")),
            dataset_record=True,
            preview_url=preview_url,
        )

def iter_file_candidates(repo: str, repo_dir: Path, license_name: str) -> Iterable[Candidate]:
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
            description="",
            prompt=text,
            license=license_name,
            content_hash=digest,
            adapter="file",
        )


def iter_candidates(repo: str, repo_dir: Path, license_name: str, kind: str) -> Iterable[Candidate]:
    if kind == "prompt-library":
        readme_candidates = list(iter_readme_prompt_candidates(repo, repo_dir, license_name))
        titled_candidates = list(iter_titled_readme_candidates(repo, repo_dir, license_name))
        if readme_candidates or titled_candidates:
            yield from readme_candidates
            yield from titled_candidates
            return
    if kind == "prompt-dataset-jsonl":
        yield from iter_jsonl_dataset_candidates(repo, repo_dir, license_name)
        return
    yield from iter_file_candidates(repo, repo_dir, license_name)


def category_for(source: dict) -> tuple[str, str]:
    repo = source["repo"].lower()
    kind = source.get("kind", "")
    if "image" in repo or "banana" in repo or "seedream" in repo or "grok" in repo:
        return "Images", "Upstream prompts"
    if "seedance" in repo:
        return "Video", "Upstream prompts"
    if "skill" in kind:
        return "Agents", "Skills"
    return "Unclassified", "Upstream"


def write_icm_card(output_root: Path, card: dict) -> None:
    card_dir = output_root / card["icm_path"]
    card_dir.mkdir(parents=True, exist_ok=True)
    (card_dir / "card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    context = (
        f"# {card['title']}\n\n"
        "## Contract\n"
        f"Use this recipe to produce a {card['category'].lower()} outcome. Preserve creator-provided constraints.\n\n"
        "## Inputs\n"
        "- Creator intent and any reference assets supplied for the run.\n\n"
        "## Process\n"
        "1. Read this card only when it matches the current task.\n"
        "2. Adapt placeholders and context without erasing source provenance.\n"
        "3. Write generated artifacts to the run output folder, never back into this reference card.\n\n"
        "## Source\n"
        f"- Repository: {card['source']['repo']}\n"
        f"- Path: {card['source']['path']}\n"
        f"- License: {card['source']['license']}\n"
        f"- Content hash: {card['source']['content_hash']}\n"
    )
    (card_dir / "CONTEXT.md").write_text(context, encoding="utf-8")


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

        category, subcategory = category_for(source)
        for candidate in iter_candidates(repo, repo_dir, license_name, source.get("kind", "")):
            if candidate.content_hash in seen_hashes:
                continue
            seen_hashes.add(candidate.content_hash)
            relative_icm_path = f"cards/{category.lower()}/{repo_name}/{candidate.content_hash[:16]}"
            card = {
                "id": f"upstream-{candidate.content_hash[:16]}",
                "slug": re.sub(r"[^a-z0-9]+", "-", candidate.title.lower()).strip("-")[:80],
                "title": candidate.title,
                "description": candidate.description,
                "prompt": candidate.prompt,
                "category": category,
                "subcategory": candidate.subcategory or subcategory,
                "tags": list(candidate.tags),
                "adapter": candidate.adapter,
                "source": {
                    "repo": candidate.repo,
                    "path": candidate.source_path,
                    "ref": source.get("source_ref", "main"),
                    "license": candidate.license,
                    "license_verified": True,
                    "content_hash": candidate.content_hash,
                },
                "icm_path": relative_icm_path,
            }
            if candidate.author:
                card["source"]["author"] = candidate.author
            if candidate.source_link:
                card["source"]["url"] = candidate.source_link
            if candidate.dataset_record:
                card["dataset_record"] = True
                card["media_type"] = "video"
                if candidate.featured:
                    card["featured"] = True
                if candidate.preview_url:
                    card["source"]["preview_url"] = candidate.preview_url
            cards.append(card)
            if not candidate.dataset_record:
                write_icm_card(output_root, card)

    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 2,
        "source": registry.get("source"),
        "cards": cards,
        "quarantine": quarantine,
        "counts": {"cards": len(cards), "quarantined_repositories": len(quarantine)},
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_root / "CONTEXT.md").write_text(
        "# Imported Creator Library\n\nRoute by task category. Load only matching card folders; do not load the full manifest into agent context.\n",
        encoding="utf-8",
    )
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
