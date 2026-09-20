from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_homepage_is_private_install_portfolio_ready():
    page = (ROOT / "frontend/src/app/page.tsx").read_text(encoding="utf-8")
    assert "AI ad factory · one-time private install" in page
    assert "Own the system that turns products into ads." in page
    assert "Get a private install" in page
    assert "Proof before promises." in page
    assert "InstallInterestForm" in page
    assert "Join the beta" not in page
    assert "BetaWaitlist" not in page


def test_install_interest_form_is_netlify_collectable_and_bot_protected():
    form = (ROOT / "frontend/src/components/InstallInterestForm.tsx").read_text(encoding="utf-8")
    assert 'name="buffer-blaster-install"' in form
    assert 'data-netlify="true"' in form
    assert 'data-netlify-honeypot="bot-field"' in form
    assert 'type="email"' in form
    assert 'name="email"' in form
    assert '"form-name": "buffer-blaster-install"' in form
    assert "Request an install" in form


def test_public_metadata_points_to_buffer_blaster_install_not_unrelated_project():
    layout = (ROOT / "frontend/src/app/layout.tsx").read_text(encoding="utf-8")
    assert "https://bufferblaster.netlify.app" in layout
    assert "stavarai-platform" not in layout
    assert "One-time private AI ad factory" in layout
    assert "Private beta" not in layout
