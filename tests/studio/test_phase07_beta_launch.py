from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_homepage_is_beta_portfolio_ready():
    page = (ROOT / "frontend/src/app/page.tsx").read_text(encoding="utf-8")
    assert "Private beta · coming soon" in page
    assert "Join the beta" in page
    assert "Find the angle." in page
    assert "Make the ad." in page
    assert "Learn what works." in page
    assert "BetaWaitlist" in page
    assert "Open Studio" not in page


def test_beta_waitlist_is_netlify_collectable_and_bot_protected():
    form = (ROOT / "frontend/src/components/BetaWaitlist.tsx").read_text(encoding="utf-8")
    assert 'name="buffer-blaster-beta"' in form
    assert 'data-netlify="true"' in form
    assert 'data-netlify-honeypot="bot-field"' in form
    assert 'type="email"' in form
    assert 'name="email"' in form
    assert '"form-name": "buffer-blaster-beta"' in form


def test_public_metadata_points_to_buffer_blaster_not_unrelated_project():
    layout = (ROOT / "frontend/src/app/layout.tsx").read_text(encoding="utf-8")
    assert "https://bufferblaster.netlify.app" in layout
    assert "stavarai-platform" not in layout
    assert "Private beta" in layout
