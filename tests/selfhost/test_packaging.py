from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_container_runs_as_non_root_and_has_healthcheck():
    dockerfile = read("Dockerfile")
    assert "USER stavarai" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "api.app:app" in dockerfile
    assert "api.main:app" not in dockerfile
    assert "--workers ${WEB_CONCURRENCY:-4}" in dockerfile


def test_compose_keeps_api_behind_caddy_and_restarts():
    compose = read("docker-compose.prod.yml")
    assert "restart: unless-stopped" in compose
    assert "./ops/selfhost/Caddyfile" in compose
    assert '"80:80"' in compose and '"443:443"' in compose
    assert '"8000:8000"' not in compose
    assert "condition: service_healthy" in compose


def test_production_env_template_never_contains_real_provider_secrets():
    env = read(".env.production.example")
    for key in [
        "MASTER_ENCRYPTION_KEY",
        "DEMO_PASSWORD",
        "BLASTER_API_KEY",
        "SUPABASE_SERVICE_KEY",
        "OPENAI_API_KEY",
        "FAL_KEY",
        "TRYPOST_API_KEY",
    ]:
        line = next(line for line in env.splitlines() if line.startswith(f"{key}="))
        assert line == f"{key}=", f"{key} must remain blank in git"
    assert "NEXT_PUBLIC_BLASTER_API_KEY" not in env


def test_one_click_installer_generates_app_owned_secrets_and_runs_preflight():
    script = read("scripts/selfhost/install.sh")
    assert "openssl rand" in script
    assert "set_env MASTER_ENCRYPTION_KEY" in script
    assert "set_env BLASTER_API_KEY" in script
    assert "set_env DEMO_PASSWORD" in script
    assert "scripts/selfhost/preflight.sh" in script
    assert "docker compose -f docker-compose.prod.yml up -d --build" in script


def test_scale_migration_is_additive_and_scoped_to_buffer_blaster():
    sql = read("supabase/migrations/006_buffer_blaster_beta_scale.sql").lower()
    assert "create index if not exists" in sql
    for forbidden in [" drop ", "delete from", "truncate ", "alter table"]:
        assert forbidden not in sql
    statement_lines = [line.strip() for line in sql.splitlines() if line.strip().startswith("on ")]
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
    for secret in ["BLASTER_API_KEY", "OPENAI_API_KEY", "FAL_KEY", "SUPABASE_SERVICE_KEY", "TRYPOST_API_KEY"]:
        assert f"NEXT_PUBLIC_{secret}" not in script
