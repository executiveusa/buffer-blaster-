from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cli_uses_guarded_factory_wallet_and_receipt_routes():
    cli = read("cli/blaster.py")
    for signal in [
        "ugc-plan",
        "ugc-execute",
        "/api/studio/ugc/factory/execute",
        "/api/studio/pricing",
        "/api/studio/billing/wallet/",
        "/api/studio/jobs",
        "human_approval_required",
        "wallet_id_required",
    ]:
        assert signal in cli
    assert "/api/studio/ugc/factory/render" not in cli


def test_agent_skill_documents_same_guarded_commercial_contract():
    skill = read("plugins/social-studio/SKILL.md")
    for signal in [
        "get_pricing",
        "get_usage_wallet",
        "execute_ugc_ad_factory",
        "server-owned",
        "final asset",
        "durable",
    ]:
        assert signal in skill
    assert "TryPost" not in skill
    assert "raw or single-clip paid generation route" in skill


def test_env_examples_expose_every_required_paid_factory_setting():
    for path in [".env.example", ".env.production.example"]:
        env = read(path)
        for signal in [
            "TRIAL_SESSION_SECRET",
            "BUFFER_BLASTER_WORKSPACE_ID=00000000-0000-0000-0000-000000000001",
            "BUFFER_BLASTER_ASSET_BUCKET",
            "MIN_CONTRIBUTION_MARGIN_BPS",
            "PAYMENT_FEE_BPS",
            "PAYMENT_FEE_FIXED_CENTS",
            "INFRASTRUCTURE_RESERVE_BPS",
            "RESEARCH_RESERVE_BPS",
            "REFUND_RESERVE_BPS",
            "STANDARD_AD_CREDIT_COST_CENTS",
            "TRIAL_7_PRICE_CENTS",
            "TRIAL_7_PROVIDER_BUDGET_CENTS",
            "TRIAL_30_PRICE_CENTS",
            "STARTER_PRICE_CENTS",
            "PRO_PRICE_CENTS",
            "UGC_FACTORY_COST_SAFETY_BPS",
            "STRIPE_TRIAL_7_PRICE_ID",
            "STRIPE_TRIAL_30_PRICE_ID",
            "STRIPE_STARTER_PRICE_ID",
            "STRIPE_PRO_PRICE_ID",
            "FAL_POLL_INTERVAL_SECONDS",
            "FAL_RENDER_TIMEOUT_SECONDS",
        ]:
            assert signal in env
    assert "STRIPE_FOUNDING_PRICE_ID" not in read(".env.production.example")


def test_default_workspace_migration_matches_deployment_contract():
    migration = read("supabase/migrations/010_buffer_blaster_default_workspace.sql")
    assert "00000000-0000-0000-0000-000000000001" in migration
    assert "insert into buffer_blaster.workspaces" in migration.lower()
    assert "on conflict (id) do update" in migration.lower()


def test_admin_settings_calls_real_integration_handshake_not_configured_echo():
    page = read("frontend/src/app/admin/settings/page.tsx")
    api = read("frontend/src/lib/api.ts")
    assert "testIntegration" in page
    assert "await testIntegration(service)" in page
    assert "/api/admin/settings/test/" in api
    assert "configured / unverified" in page
    assert "setTimeout" not in page
    assert "!!key?.configured" not in page


def test_campaign_page_uses_canonical_planner_and_labels_simulation():
    page = read("frontend/src/app/studio/campaigns/page.tsx")
    client = read("frontend/src/lib/campaign-api.ts")
    assert "createCampaignPlan" in page
    assert "await createCampaignPlan" in page
    assert "/api/studio/campaigns/plan" in client
    assert "Simulation only" in page
    assert "No invented campaign cards" in page
    assert "const formats =" not in page


def test_calendar_starts_empty_and_uses_real_account_and_receipt_contract():
    page = read("frontend/src/app/studio/calendar/page.tsx")
    for signal in [
        "listSocialAccounts",
        "scheduleDrop",
        "social_account_id",
        "scheduled_at",
        "Only receipts count as scheduled",
        "No schedule receipt in this session",
        "Human approval",
    ]:
        assert signal in page
    assert "const items:" not in page
    assert "TryPost" not in page
    assert "3 items need review" not in page


def test_ci_exercises_paid_pass_trial_routes_and_fresh_schema():
    wf_path = ROOT / ".github/workflows/test-api.yml"
    if not wf_path.exists():
        pytest.skip(".github/workflows/test-api.yml not present in runtime environment")
    workflow = read(".github/workflows/test-api.yml")
    for signal in [
        "/api/checkout/offer",
        '"offer":"trial-7"',
        "/api/trial/activate",
        "/api/trial/status",
        "/api/trial/execute",
        '"error":"guarded_factory_required"',
        "Fresh PostgreSQL schema proof",
        "010_buffer_blaster_default_workspace.sql",
    ]:
        assert signal in workflow


def test_wiring_truth_rollback_receipt_exists_and_preserves_additive_db():
    rollback = read("ops/rollback/wiring-truth-pricing-v2.json")
    assert '"baseline_main_sha": "49845ea9882df8b32ad9772b6dc467d39bda172b"' in rollback
    assert '"destructive_sql": false' in rollback
    assert "do not drop it during emergency rollback" in rollback
