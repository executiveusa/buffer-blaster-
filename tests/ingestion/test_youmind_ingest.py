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
    assert card["icm_path"].startswith("library/imported/allowed/")
    assert {item["reason"] for item in result["quarantine"]} == {"license-unverified", "source-not-present"}
    assert (output / "manifest.json").exists()


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
