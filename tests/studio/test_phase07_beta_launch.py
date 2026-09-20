from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_homepage_is_private_install_portfolio_ready():
    page = (ROOT / "frontend/src/app/page.tsx").read_text(encoding="utf-8")
    assert "AI video ad factory · private install" in page
    assert "Create AI ads." in page
    assert "Own the factory." in page
    assert "Watch real output" in page
    assert "Selva & Sea" in page
    assert "Placeholder only · not proof" in page
    assert "Request a private install" in page
    assert "Private beta · coming soon" not in page
    assert "Join the beta" not in page


def test_install_inquiry_has_durable_api_transport_and_bot_field():
    form = (ROOT / "frontend/src/components/InstallInquiry.tsx").read_text(encoding="utf-8")
    route = (ROOT / "frontend/src/app/api/install-inquiry/route.ts").read_text(encoding="utf-8")
    assert '/api/install-inquiry' in form
    assert 'bot_field' in form
    assert 'data-netlify' not in form
    assert '/api/install-inquiries' in route


def test_public_metadata_points_to_buffer_blaster_not_unrelated_project():
    layout = (ROOT / "frontend/src/app/layout.tsx").read_text(encoding="utf-8")
    robots = (ROOT / "frontend/src/app/robots.ts").read_text(encoding="utf-8")
    sitemap = (ROOT / "frontend/src/app/sitemap.ts").read_text(encoding="utf-8")
    public_meta = "\n".join([layout, robots, sitemap])
    assert "SITE_URL" in public_meta
    assert "bufferblaster.netlify.app" not in public_meta
    assert "stavarai-platform" not in public_meta
    assert "Create AI ads. Own the factory." in layout
    assert "Private beta" not in layout
