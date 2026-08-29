from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_container_runs_as_non_root_and_has_healthcheck():
    dockerfile = read("Dockerfile")
    assert "USER stavarai" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "ffmpeg" in dockerfile


def test_compose_binds_public_ports_only_on_caddy():
    compose = read("docker-compose.prod.yml")
    assert '"80:80"' in compose
    assert '"443:443"' in compose
    assert "redis_data:" in compose
    assert "--requirepass" in compose


def test_caddy_proxies_to_api():
    caddy = read("ops/selfhost/Caddyfile")
    assert "reverse_proxy api:8000" in caddy


def test_env_contract_keeps_core_and_integration_secrets_private():
    env = read(".env.production.example")
    for key in ["MASTER_ENCRYPTION_KEY", "BLASTER_API_KEY", "REDIS_URL", "SUPABASE_SERVICE_KEY", "FAL_KEY"]:
        assert key in env
    assert "NEXT_PUBLIC_FAL" not in env
    assert "NEXT_PUBLIC_SUPABASE_SERVICE" not in env


def test_one_click_installer_generates_app_owned_secrets_and_runs_preflight():
    script = read("scripts/selfhost/install.sh")
    assert "openssl rand" in script
    assert "set_env MASTER_ENCRYPTION_KEY" in script
    assert "set_env BLASTER_API_KEY" in script
    assert "set_env DEMO_PASSWORD" in script
    assert "scripts/selfhost/preflight.sh" in script
    assert "docker compose -f docker-compose.prod.yml up -d --build" in script
    assert "--redis-url" in script


def test_preflight_requires_redis_url():
    preflight = read("scripts/selfhost/preflight.sh")
    assert "REDIS_URL" in preflight


def test_buffer_blaster_schema_exists_before_additive_scale_indexes():
    schema = read("supabase/migrations/007_buffer_blaster_schema.sql").lower()
    indexes = read("supabase/migrations/008_buffer_blaster_beta_scale.sql").lower()
    for table in ["campaigns", "creative_jobs", "content_items", "approvals", "publish_jobs", "publish_receipts", "model_runs", "performance_events", "source_assets", "ugc_characters", "usage_wallets"]:
        assert f"create table if not exists buffer_blaster.{table}" in schema
    assert "create index if not exists" in indexes
    for forbidden in [" drop ", "delete from", "truncate ", "alter table"]:
        assert forbidden not in indexes
    statement_lines = [line.strip() for line in indexes.splitlines() if line.strip().startswith("on ")]
    assert statement_lines
    assert all("buffer_blaster." in line for line in statement_lines)


def test_live_publishing_gate_is_still_present():
    studio = read("api/routers/studio.py")
    publishing = read("api/services/publishing.py")
    assert "approved=drop.approved" in studio
    assert "if not request.approved" in publishing
    assert '"error": "human_approval_required"' in publishing


def test_production_cors_honors_explicit_allowed_origins():
    app = read("api/app.py")
    assert 'os.getenv("ALLOWED_ORIGINS", "")' in app
    assert "allow_origins=_allowed_origins()" in app
    assert "https://stavarai-platform.vercel.app" in app


def test_vercel_helper_exposes_only_public_live_mode_values():
    script = read("scripts/selfhost/configure-vercel.sh")
    assert "NEXT_PUBLIC_DEMO_MODE" in script
    assert "NEXT_PUBLIC_PUBLIC_CONSOLE" in script
    assert "NEXT_PUBLIC_API_URL" in script
