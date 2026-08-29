from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_leads_with_testable_ad_outcome_not_generic_content_cadence():
    page = _read("frontend/src/app/page.tsx")
    for phrase in ["Find the angle.", "Make the ad.", "Prove what works."]:
        assert phrase in page
    assert "research" in page.lower()
    assert "receipt" in page.lower()
    assert "winning ads" not in page.lower()


def test_global_metadata_matches_launch_positioning():
    layout = _read("frontend/src/app/layout.tsx")
    assert "Find the angle" in layout
    assert "Make the content. Keep the cadence." not in layout


def test_pricing_has_one_launch_revenue_offer():
    page = _read("frontend/src/app/pricing/page.tsx")
    assert "Founding Ad Batch" in page
    assert "$249" in page
    assert "3 vertical UGC ads" in page
    assert "Creator\", price" not in page
    assert "Growth\", price" not in page
    assert "Agency\", price" not in page


def test_create_surface_is_factory_plan_first_and_shows_trust_states():
    page = _read("frontend/src/app/studio/create/page.tsx")
    for phrase in [
        "Build batch plan",
        "Customer pain",
        "Product mechanism",
        "Approve & render clip 1",
        "Gate passed",
        "Render receipt",
    ]:
        assert phrase in page
    assert "Build prompt" not in page


def test_studio_shell_uses_approval_state_not_fake_credit_usage():
    shell = _read("frontend/src/components/studio-shell.tsx")
    assert "Approval gate" in shell
    assert "UGC credits" not in shell
    assert "Growth workspace" not in shell


def test_public_launch_copy_keeps_internal_codenames_out():
    public = "\n".join([
        _read("frontend/src/app/page.tsx"),
        _read("frontend/src/app/pricing/page.tsx"),
        _read("frontend/src/app/layout.tsx"),
    ]).lower()
    for codename in ["buffer blaster", "stavarai", "hermes", "higgsfield"]:
        assert codename not in public
