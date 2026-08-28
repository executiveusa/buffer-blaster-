from pathlib import Path


def test_agentic_social_studio_icm_walk_contracts_exist():
    root = Path(__file__).resolve().parents[2]
    required = [
        root / "icm" / "CONTEXT.md",
        root / "icm" / "_system" / "CONTEXT.md",
        root / "icm" / "_templates" / "campaign" / "CONTEXT.md",
        root / "icm" / "_templates" / "campaign" / "01_brief" / "CONTEXT.md",
        root / "icm" / "_templates" / "campaign" / "02_create" / "CONTEXT.md",
        root / "icm" / "_templates" / "campaign" / "03_review_publish" / "CONTEXT.md",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    assert not missing, f"ICM walk contract missing: {missing}"


def test_root_agents_is_a_small_router():
    root = Path(__file__).resolve().parents[2]
    lines = (root / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 60, "AGENTS.md must route, not carry payload"
