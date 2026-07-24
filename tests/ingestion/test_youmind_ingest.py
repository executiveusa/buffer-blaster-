import json
from pathlib import Path

from scripts.youmind_ingest import compile_registry


def write_repo(root: Path, name: str, license_text: str | None, files: dict[str, str]) -> None:
    repo = root / name
    repo.mkdir(parents=True)
    if license_text is not None:
        (repo / "LICENSE").write_text(license_text, encoding="utf-8")
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_compiler_preserves_provenance_dedupes_and_quarantines(tmp_path: Path) -> None:
    registry = {
        "source": "YouMind-OpenLab",
        "repositories": [
            {"repo": "YouMind-OpenLab/allowed", "license_status": "verified", "license": "MIT"},
            {"repo": "YouMind-OpenLab/unknown", "license_status": "unverified"},
            {"repo": "YouMind-OpenLab/missing", "license_status": "unverified"},
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    source_root = tmp_path / "sources"
    source_root.mkdir()

    prompt = "Create a cinematic launch image with dramatic side lighting and a clear product focal point."
    write_repo(
        source_root,
        "allowed",
        "MIT License\nPermission is hereby granted, free of charge...",
        {"prompts/hero.md": prompt, "prompts/duplicate.txt": prompt, "README.md": "ignore this documentation"},
    )
    write_repo(
        source_root,
        "unknown",
        None,
        {"prompts/private.md": "This content must remain quarantined because no license is verified."},
    )

    output = tmp_path / "output"
    result = compile_registry(registry_path, source_root, output)

    assert result["counts"] == {"cards": 1, "quarantined_repositories": 2}
    card = result["cards"][0]
    assert card["source"]["repo"] == "YouMind-OpenLab/allowed"
    assert card["source"]["path"] == "prompts/duplicate.txt"
    assert card["source"]["license"] == "MIT"
    assert card["source"]["license_verified"] is True
    assert len(card["source"]["content_hash"]) == 64
    assert card["icm_path"].startswith("cards/unclassified/allowed/")
    assert {item["reason"] for item in result["quarantine"]} == {"license-unverified", "source-not-present"}
    assert (output / "manifest.json").exists()
    assert (output / "CONTEXT.md").exists()
    card_dir = output / card["icm_path"]
    assert (card_dir / "card.json").exists()
    assert (card_dir / "CONTEXT.md").exists()


def test_detected_cc_by_license_is_allowed(tmp_path: Path) -> None:
    registry = {
        "source": "YouMind-OpenLab",
        "repositories": [{"repo": "YouMind-OpenLab/cc-library", "license_status": "unverified"}],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    source_root = tmp_path / "sources"
    source_root.mkdir()
    write_repo(
        source_root,
        "cc-library",
        "Creative Commons Attribution 4.0 International License (CC BY 4.0)",
        {"prompts/example.md": "A sufficiently detailed prompt for a clean editorial portrait with natural window light."},
    )

    result = compile_registry(registry_path, source_root, tmp_path / "output")
    assert result["counts"]["cards"] == 1
    assert result["cards"][0]["source"]["license"] == "CC-BY-4.0"


def test_numbered_readme_prompt_library_extracts_individual_cards(tmp_path: Path) -> None:
    registry = {
        "source": "YouMind-OpenLab",
        "repositories": [
            {
                "repo": "YouMind-OpenLab/awesome-nano-banana-pro-prompts",
                "kind": "prompt-library",
                "license_status": "verified",
                "license": "CC-BY-4.0",
                "source_ref": "sample-commit-sha",
            }
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    source_root = tmp_path / "sources"
    source_root.mkdir()
    readme = """
# Prompt Library

### No. 1: Wide quote card with portrait

#### 📖 Description
A reusable quote card for social media.

#### 📝 Prompt
```text
A wide quote card with a portrait on the left and elegant quote typography on the right, using warm editorial lighting.
```

#### 🖼️ Generated Images
image here

### No. 2: Premium ecommerce hero

#### 📖 Description
A product hero composition for ecommerce.

#### 📝 Prompt
```
Create a premium ecommerce hero image of a single product on a seamless studio backdrop with controlled rim lighting.
```
"""
    write_repo(
        source_root,
        "awesome-nano-banana-pro-prompts",
        "Creative Commons Attribution 4.0 International License (CC BY 4.0)",
        {"README.md": readme},
    )

    output = tmp_path / "output"
    result = compile_registry(registry_path, source_root, output)

    assert result["counts"]["cards"] == 2
    assert [card["title"] for card in result["cards"]] == [
        "Wide quote card with portrait",
        "Premium ecommerce hero",
    ]
    first = result["cards"][0]
    assert first["adapter"] == "numbered-readme"
    assert first["category"] == "Images"
    assert first["description"] == "A reusable quote card for social media."
    assert first["source"]["path"] == "README.md#no-1"
    assert first["source"]["ref"] == "sample-commit-sha"
    assert (output / first["icm_path"] / "card.json").exists()
    context = (output / first["icm_path"] / "CONTEXT.md").read_text(encoding="utf-8")
    assert "Repository: YouMind-OpenLab/awesome-nano-banana-pro-prompts" in context
    assert "License: CC-BY-4.0" in context
