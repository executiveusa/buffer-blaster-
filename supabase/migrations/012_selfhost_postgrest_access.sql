-- 012_selfhost_postgrest_access.sql
-- Explicit PostgREST access contract for the self-hosted Buffer Blaster schema.
-- RLS remains enabled. anon/authenticated receive schema USAGE only; service_role
-- and postgres receive table/sequence privileges required by the backend.

GRANT USAGE ON SCHEMA buffer_blaster TO postgres, anon, authenticated, service_role;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA buffer_blaster TO postgres, service_role;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA buffer_blaster TO postgres, service_role;

-- Keep future additive tables/sequences service-role accessible without granting
-- direct table privileges to anon/authenticated users.
ALTER DEFAULT PRIVILEGES IN SCHEMA buffer_blaster
  GRANT ALL PRIVILEGES ON TABLES TO postgres, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA buffer_blaster
  GRANT ALL PRIVILEGES ON SEQUENCES TO postgres, service_role;

COMMENT ON SCHEMA buffer_blaster IS
  'Canonical Buffer Blaster state. PostgREST schema is exposed on self-hosted Supabase; table access remains service-role only unless explicit RLS-backed grants are added.';
