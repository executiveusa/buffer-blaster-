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


TITLED_README = """# Awesome Prompts

## All Prompts

### Luxury Perfume Commercial

![English](https://img.shields.io/badge/lang-English-blue)

> A cinematic luxury perfume commercial with controlled camera movement.

#### 📝 Prompt

```
Cinematic luxury perfume commercial, 10 seconds. A elegant woman holds a dark navy
glass bottle toward the camera, soft pale studio background, shallow depth of field.
```

**Author:** [Elisia](https://x.com/example) | **Source:** [Link](https://x.com/example/status/1) | **Published:** Sep 18, 2026

---
### Too Short

#### 📝 Prompt

```
tiny
```
"""


def test_titled_readme_adapter_extracts_attribution(tmp_path: Path) -> None:
    registry = {
        "source": "YouMind-OpenLab",
        "repositories": [
            {"repo": "YouMind-OpenLab/awesome-x", "kind": "prompt-library", "license_status": "verified", "license": "CC-BY-4.0"},
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    source_root = tmp_path / "sources"
    write_repo(source_root, "awesome-x", "Creative Commons Attribution 4.0", {"README.md": TITLED_README})

    result = compile_registry(registry_path, source_root, tmp_path / "out")

    assert result["counts"] == {"cards": 1, "quarantined_repositories": 0}
    card = result["cards"][0]
    assert card["adapter"] == "titled-readme"
    assert card["title"] == "Luxury Perfume Commercial"
    assert card["description"].startswith("A cinematic luxury perfume commercial")
    assert card["source"]["author"] == "Elisia"
    assert card["source"]["url"] == "https://x.com/example/status/1"
    assert card["source"]["license_verified"] is True


def test_jsonl_dataset_adapter_dedupes_and_skips_card_folders(tmp_path: Path) -> None:
    registry = {
        "source": "Goku-OpenLab",
        "repositories": [
            {"repo": "Goku-OpenLab/seedance-x", "kind": "prompt-dataset-jsonl", "license_status": "verified", "license": "CC-BY-4.0"},
        ],
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    prompt = "A cinematic tracking shot through a rainy neon alley at night, shallow depth of field."
    records = [
        {"id": "SD2_00001", "slug": "neon-alley", "category": "Commercial", "is_featured": True,
         "file_name": "seedance-2/videos/SD2_00001.mp4", "sourceLink": "https://example.com/post1",
         "i18n": {"en": {"p": prompt, "t": "Neon Alley", "tags": ["cinematic", "night"]}}},
        {"id": "SD2_00002", "slug": "neon-alley-dupe", "category": "Commercial", "is_featured": False,
         "i18n": {"en": {"p": prompt, "t": "Neon Alley Dupe", "tags": []}}},
        {"id": "SD2_00003", "slug": "blank", "category": "Commercial", "i18n": {"en": {"p": "", "t": "Blank"}}},
    ]
    source_root = tmp_path / "sources"
    write_repo(
        source_root,
        "seedance-x",
        "Creative Commons Attribution 4.0",
        {"metadata.jsonl": "\n".join(json.dumps(r) for r in records)},
    )

    output = tmp_path / "out"
    result = compile_registry(registry_path, source_root, output)

    assert result["counts"] == {"cards": 1, "quarantined_repositories": 0}
    card = result["cards"][0]
    assert card["adapter"] == "jsonl-dataset"
    assert card["dataset_record"] is True
    assert card["featured"] is True
    assert card["tags"] == ["cinematic", "night"]
    assert card["subcategory"] == "Seedance 2 · Commercial"
    assert card["source"]["url"] == "https://example.com/post1"
    assert card["source"]["preview_url"].endswith("seedance-2/videos/SD2_00001.mp4")
    assert not (output / card["icm_path"]).exists(), "dataset records must not create ICM card folders"
    assert (output / "manifest.json").exists()
