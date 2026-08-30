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


def test_pricing_uses_paid_test_passes_and_margin_safe_ad_credits():
    page = _read("frontend/src/app/pricing/page.tsx")
    for phrase in [
        "7-Day Test Drive",
        "$19",
        "3 Ad Credits",
        "30-Day Launch Pass",
        "$49",
        "8 Ad Credits",
        "$99",
        "$199",
        "under $1",
        "unused trial credits expire",
    ]:
        assert phrase.lower() in page.lower()
    assert "free trial" not in page.lower()
    assert "Founding Ad Batch" not in page
    assert "3 vertical UGC ads" not in page


def test_create_surface_is_factory_plan_first_and_finishes_the_ad():
    page = _read("frontend/src/app/studio/create/page.tsx")
    for phrase in [
        "Build ad plan",
        "Customer pain",
        "Product mechanism",
        "Estimated generation reserve",
        "Credits required",
        "build final ad",
        "Gate passed",
        "Factory receipt",
    ]:
        assert phrase.lower() in page.lower()
    assert "Approve & render clip 1" not in page


def test_studio_shell_uses_approval_state_not_fake_credit_usage():
    shell = _read("frontend/src/components/studio-shell.tsx")
    assert "Approval gate" in shell
    assert "Growth workspace" not in shell


def test_public_launch_copy_keeps_internal_codenames_out():
    public = "\n".join([_read("frontend/src/app/page.tsx"), _read("frontend/src/app/pricing/page.tsx")]).lower()
    for codename in ["buffer blaster", "stavarai", "hermes", "higgsfield"]:
        assert codename not in public


def test_live_studio_does_not_hardcode_fake_operating_metrics():
    overview = _read("frontend/src/app/studio/page.tsx")
    library = _read("frontend/src/app/studio/library/page.tsx")
    analytics = _read("frontend/src/app/studio/analytics/page.tsx")
    for fake in ["84.2K", "6.4K", "1,284", "Attributed orders", "2 videos processing", "3 awaiting review", "Active campaigns\" value=\"4"]:
        assert fake not in overview
        assert fake not in library
        assert fake not in analytics
    assert "No performance evidence yet" in analytics
