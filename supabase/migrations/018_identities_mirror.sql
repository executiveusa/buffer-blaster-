-- 018_identities_mirror.sql
-- Mirror of the Redis identity registry (characters/products/locations), the
-- same pattern as 016's agent audit mirror: Redis is the runtime source of
-- truth; this table is the durable, queryable copy the API upserts
-- best-effort. Members read through RLS; all writes stay service-role (API).
-- Shots/takes execution is NOT implemented yet; generated media lineage
-- already lives in buffer_blaster.media_takes (migration 013).

CREATE TABLE IF NOT EXISTS buffer_blaster.identities (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('character','product','location')),
  name text NOT NULL CHECK (char_length(name) BETWEEN 2 AND 80),
  photos text[] NOT NULL DEFAULT '{}',
  sheet_url text,
  identity_block text NOT NULL DEFAULT '',
  created_by text NOT NULL,
  deleted boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, id)
);

CREATE INDEX IF NOT EXISTS identities_workspace_kind_idx
  ON buffer_blaster.identities (workspace_id, kind) WHERE NOT deleted;

ALTER TABLE buffer_blaster.identities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS identities_read_members ON buffer_blaster.identities;
CREATE POLICY identities_read_members ON buffer_blaster.identities
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);

GRANT SELECT ON buffer_blaster.identities TO authenticated;
GRANT ALL PRIVILEGES ON buffer_blaster.identities TO postgres, service_role;

COMMENT ON TABLE buffer_blaster.identities IS 'Mirror of the Redis identity registry; runtime truth stays in Redis (016 mirror pattern).';
