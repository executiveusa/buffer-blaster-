import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.icm_bundle import build_bundle


def make_library(root: Path, *, verified: bool = True, icm_path: str = "cards/images/example/abc123") -> Path:
    library = root / "library"
    card_dir = library / icm_path
    card_dir.mkdir(parents=True)
    prompt = "Create a premium product photograph on a clean studio backdrop."
    card = {
        "id": "upstream-abc123",
        "title": "Example Creator Card",
        "description": "A bounded test recipe.",
        "prompt": prompt,
        "category": "Images",
        "subcategory": "Upstream prompts",
        "tags": ["product", "studio"],
        "source": {
            "repo": "YouMind-OpenLab/example",
            "path": "README.md#no-1",
            "ref": "deadbeef",
            "license": "CC-BY-4.0",
            "license_verified": verified,
            "content_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
        "icm_path": icm_path,
    }
    manifest = {"schema_version": 2, "source": "YouMind-OpenLab", "cards": [card], "quarantine": [], "counts": {"cards": 1, "quarantined_repositories": 0}}
    (library / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (card_dir / "card.json").write_text(json.dumps(card), encoding="utf-8")
    (card_dir / "CONTEXT.md").write_text("# Example Creator Card\n\nUse only for a matching image task.\n", encoding="utf-8")
    return library


def test_bundle_is_deterministic_and_contains_icm_contracts(tmp_path: Path) -> None:
    library = make_library(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    receipt_one = build_bundle(library, first)
    receipt_two = build_bundle(library, second)

    assert first.read_bytes() == second.read_bytes()
    assert receipt_one["sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    assert receipt_one["sha256"] == receipt_two["sha256"]
    assert receipt_one["cards"] == 1

    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert "AGENTS.md" in names
        assert "CONTEXT.md" in names
        assert "README.md" in names
        assert "manifest.json" in names
        assert "output/.gitkeep" in names
        assert "cards/images/example/abc123/card.json" in names
        assert "cards/images/example/abc123/CONTEXT.md" in names
        router = archive.read("CONTEXT.md").decode("utf-8")
        assert "do not load the entire library" in router.lower()
        agents = archive.read("AGENTS.md").decode("utf-8")
        assert "Human review is required" in agents

    receipt_path = first.with_suffix(".zip.receipt.json")
    assert receipt_path.exists()
    saved = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert saved["sha256"] == receipt_one["sha256"]


def test_bundle_rejects_unverified_license(tmp_path: Path) -> None:
    library = make_library(tmp_path, verified=False)
    with pytest.raises(ValueError, match="unverified license"):
        build_bundle(library, tmp_path / "blocked.zip")


def test_bundle_rejects_missing_card_artifact(tmp_path: Path) -> None:
    library = make_library(tmp_path)
    (library / "cards/images/example/abc123/CONTEXT.md").unlink()
    with pytest.raises(FileNotFoundError, match="missing card artifact"):
        build_bundle(library, tmp_path / "blocked.zip")


def test_bundle_rejects_tampered_card_artifact(tmp_path: Path) -> None:
    library = make_library(tmp_path)
    card_path = library / "cards/images/example/abc123/card.json"
    artifact = json.loads(card_path.read_text(encoding="utf-8"))
    artifact["prompt"] = "Tampered prompt that does not match the reviewed manifest."
    card_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact differs from manifest field prompt"):
        build_bundle(library, tmp_path / "blocked.zip")


def test_bundle_rejects_absolute_icm_path(tmp_path: Path) -> None:
    library = make_library(tmp_path)
    manifest_path = library / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cards"][0]["icm_path"] = "/tmp/outside-card"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe icm_path"):
        build_bundle(library, tmp_path / "blocked.zip")
