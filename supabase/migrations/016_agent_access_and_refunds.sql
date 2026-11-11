-- 016_agent_access_and_refunds.sql
-- Durable audit mirror for agent tokens, human approvals and wallet refunds.
-- Redis remains the runtime authority (atomic Lua); these rows are written
-- best-effort by the API with the service role for reporting and audit.
-- Token secrets are NEVER stored here (not even hashes).

CREATE TABLE IF NOT EXISTS buffer_blaster.agent_tokens (
  id text PRIMARY KEY CHECK (char_length(id) BETWEEN 8 AND 64),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  name text NOT NULL CHECK (char_length(name) BETWEEN 2 AND 80),
  scopes text[] NOT NULL DEFAULT '{}'::text[]
    CHECK (scopes <@ ARRAY['read','plan','render','publish']::text[]),
  created_by text,
  expires_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_tokens_workspace_idx
  ON buffer_blaster.agent_tokens (workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS buffer_blaster.agent_approvals (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('render','publish')),
  status text NOT NULL CHECK (status IN ('pending','approved','rejected','consumed')),
  payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
  max_cost_cents integer NOT NULL DEFAULT 0 CHECK (max_cost_cents >= 0),
  requested_by text NOT NULL,
  decided_by text,
  summary text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_approvals_workspace_status_idx
  ON buffer_blaster.agent_approvals (workspace_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS buffer_blaster.wallet_reservation_releases (
  id text PRIMARY KEY,                       -- "<wallet_id>:<idempotency_key>", one row per reservation
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  wallet_id text NOT NULL REFERENCES buffer_blaster.usage_wallets(id) ON DELETE CASCADE,
  idempotency_key text NOT NULL,
  refunded_provider_budget_cents integer NOT NULL CHECK (refunded_provider_budget_cents >= 0),
  refunded_ad_credits integer NOT NULL CHECK (refunded_ad_credits >= 0),
  provider_cost_incurred_cents integer NOT NULL DEFAULT 0 CHECK (provider_cost_incurred_cents >= 0),
  reason text NOT NULL,
  released_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (wallet_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS wallet_releases_workspace_idx
  ON buffer_blaster.wallet_reservation_releases (workspace_id, released_at DESC);

ALTER TABLE buffer_blaster.agent_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.agent_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.wallet_reservation_releases ENABLE ROW LEVEL SECURITY;

-- Explicit grants (012 default privileges also cover new tables; this is idempotent).
GRANT ALL PRIVILEGES ON buffer_blaster.agent_tokens, buffer_blaster.agent_approvals,
  buffer_blaster.wallet_reservation_releases TO postgres, service_role;

COMMENT ON TABLE buffer_blaster.agent_tokens IS 'Agent token metadata (no secrets). Runtime authority: Redis.';
COMMENT ON TABLE buffer_blaster.agent_approvals IS 'Human approvals for agent render/publish. Runtime authority: Redis.';
COMMENT ON TABLE buffer_blaster.wallet_reservation_releases IS 'Full refunds of reservations whose job produced no final ad.';
