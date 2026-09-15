from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_leads_with_testable_creative_outcome_not_generic_content_cadence():
    page = _read("frontend/src/app/page.tsx")
    for phrase in ["Make a better ad.", "Know what it costs.", "Create an ad"]:
        assert phrase in page
    assert "From brief to finished ad." in page
    assert "research" in page.lower()
    assert "evidence" in page.lower()
    assert "winning ads" not in page.lower()
    assert "$19" not in page
    assert "$49" not in page


def test_global_metadata_matches_buffer_blaster_positioning():
    layout = _read("frontend/src/app/layout.tsx")
    assert "Buffer Blaster" in layout
    assert "Make better UGC ads" in layout
    assert "Social Studio" not in layout


def test_access_page_sells_managed_outcome_and_private_install_not_token_plans():
    page = _read("frontend/src/app/pricing/page.tsx")
    for phrase in [
        "Choose how you want to work",
        "Managed",
        "Private install",
        "Studio, REST, MCP, and CLI",
        "Approval before spend",
    ]:
        assert phrase.lower() in page.lower()
    for retired_public_offer in ["7-Day Test Drive", "$19", "$49", "$99", "$199", "Ad Credits", "CheckoutButton"]:
        assert retired_public_offer.lower() not in page.lower()


def test_create_surface_is_factory_plan_first_and_finishes_the_ad():
    page = _read("frontend/src/app/studio/create/page.tsx")
    for phrase in [
        "Review scripts and cost",
        "Customer pain",
        "Product mechanism",
        "Estimated cost",
        "Credits required",
        "and render",
        "Gate passed",
        "Receipt",
    ]:
        assert phrase.lower() in page.lower()
    assert "Approve & render clip 1" not in page


def test_studio_shell_uses_approval_state_not_fake_credit_usage():
    shell = _read("frontend/src/components/studio-shell.tsx")
    assert "Approvals" in shell
    assert "Growth workspace" not in shell


def test_public_launch_copy_uses_buffer_blaster_identity_without_internal_codenames():
    public = "\n".join([_read("frontend/src/app/page.tsx"), _read("frontend/src/app/pricing/page.tsx")]).lower()
    assert "buffer blaster" in public
    assert "social studio" not in public
    for codename in ["stavarai", "hermes", "higgsfield"]:
        assert codename not in public


def test_public_copy_does_not_claim_unverified_provider_state():
    public = "\n".join([_read("frontend/src/app/page.tsx"), _read("frontend/src/app/pricing/page.tsx")]).lower()
    for unsafe_claim in ["meta connected", "tiktok connected", "shopify connected", "guaranteed roas", "guaranteed conversion"]:
        assert unsafe_claim not in public
    assert "your provider accounts and limits" in public


def test_live_studio_does_not_hardcode_fake_operating_metrics():
    overview = _read("frontend/src/app/studio/page.tsx")
    library = _read("frontend/src/app/studio/library/page.tsx")
    analytics = _read("frontend/src/app/studio/analytics/page.tsx")
    for fake in ["84.2K", "6.4K", "1,284", "Attributed orders", "2 videos processing", "3 awaiting review", "Active campaigns\" value=\"4"]:
        assert fake not in overview
        assert fake not in library
        assert fake not in analytics
    assert "No results yet" in analytics
