-- 019_usage_events.sql
-- Append-only spend ledger (S4). One row per provider call, written only via
-- record_usage() (service role). actual_cents stays NULL until the provider
-- reports it - estimated and actual are never mixed. Members read through
-- RLS; UPDATE/DELETE are blocked by trigger so the ledger stays append-only.

CREATE TABLE IF NOT EXISTS buffer_blaster.usage_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- RESTRICT, deliberately: the ledger is append-only, so a workspace that has
  -- usage rows cannot be deleted (the cascade would either silently destroy
  -- audit history or fail on the trigger). Decommission a workspace by
  -- revoking access, not by deleting its ledger.
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE RESTRICT,
  job_id text,
  approval_id text,
  actor text NOT NULL,                 -- user:<uuid> | agent:<name> | api-key
  provider text NOT NULL,
  model text NOT NULL,
  reasoning_level text,
  kind text NOT NULL CHECK (kind IN ('llm','vision','image','video','transcribe')),
  tokens_in integer CHECK (tokens_in IS NULL OR tokens_in >= 0),
  tokens_out integer CHECK (tokens_out IS NULL OR tokens_out >= 0),
  estimated_cents integer CHECK (estimated_cents IS NULL OR estimated_cents >= 0),
  actual_cents integer CHECK (actual_cents IS NULL OR actual_cents >= 0),
  wallet_credits integer CHECK (wallet_credits IS NULL OR wallet_credits >= 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS usage_events_workspace_day_idx
  ON buffer_blaster.usage_events (workspace_id, created_at);
CREATE INDEX IF NOT EXISTS usage_events_workspace_job_idx
  ON buffer_blaster.usage_events (workspace_id, job_id);
CREATE INDEX IF NOT EXISTS usage_events_workspace_model_idx
  ON buffer_blaster.usage_events (workspace_id, model);

-- Append-only: no UPDATE, no DELETE, ever.
CREATE OR REPLACE FUNCTION buffer_blaster.usage_events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'usage_events is append-only';
END $$;
DROP TRIGGER IF EXISTS usage_events_no_update ON buffer_blaster.usage_events;
CREATE TRIGGER usage_events_no_update BEFORE UPDATE OR DELETE ON buffer_blaster.usage_events
  FOR EACH ROW EXECUTE FUNCTION buffer_blaster.usage_events_append_only();

ALTER TABLE buffer_blaster.usage_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS usage_read_members ON buffer_blaster.usage_events;
CREATE POLICY usage_read_members ON buffer_blaster.usage_events
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);

GRANT SELECT ON buffer_blaster.usage_events TO authenticated;
GRANT ALL PRIVILEGES ON buffer_blaster.usage_events TO postgres, service_role;

COMMENT ON TABLE buffer_blaster.usage_events IS 'Append-only spend ledger: one row per provider call. actual_cents only from provider responses; estimated vs actual never mixed (S4).';
