from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase4_adds_postgrest_grants_without_public_table_grants():
    migration = read("supabase/migrations/012_selfhost_postgrest_access.sql").lower()
    assert "grant usage on schema buffer_blaster" in migration
    assert "postgres, anon, authenticated, service_role" in migration
    assert "grant all privileges on all tables in schema buffer_blaster to postgres, service_role" in migration
    assert "to anon" not in migration
    assert "to authenticated" not in migration


def test_api_and_worker_join_configurable_selfhost_supabase_network():
    compose = read("docker-compose.prod.yml")
    assert "selfhost_supabase:" in compose
    assert "SUPABASE_DOCKER_NETWORK" in compose
    assert "supabase_default" in compose
    assert compose.count("- selfhost_supabase") >= 2


def test_env_uses_container_reachable_selfhost_supabase_example():
    env = read(".env.production.example")
    assert "SUPABASE_DOCKER_NETWORK=supabase_default" in env
    assert "SUPABASE_URL=http://supabase-kong:8000" in env
    assert "SUPABASE_URL=http://127.0.0.1" not in env
    assert "SUPABASE_URL=https://" not in env or "supabase.co" not in env


def test_preflight_rejects_managed_and_container_local_supabase_routes():
    preflight = read("scripts/selfhost/preflight.sh")
    assert "supabase.co" in preflight
    assert "127.0.0.1" in preflight
    assert "localhost" in preflight
    assert "docker network inspect" in preflight
    assert "SELF-HOSTED SUPABASE ROUTE READY" in preflight
