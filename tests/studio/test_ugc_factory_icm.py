from pathlib import Path


def test_ugc_factory_icm_walk_contracts_exist():
    root = Path(__file__).resolve().parents[2]
    base = root / "icm" / "_templates" / "ugc_ad_factory"
    required = [
        base / "CONTEXT.md",
        base / "01_research" / "CONTEXT.md",
        base / "02_script_gate" / "CONTEXT.md",
        base / "03_cast" / "CONTEXT.md",
        base / "04_generate" / "CONTEXT.md",
        base / "05_seam_qa" / "CONTEXT.md",
        base / "06_deliver" / "CONTEXT.md",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    assert not missing, f"UGC factory ICM walk contract missing: {missing}"
