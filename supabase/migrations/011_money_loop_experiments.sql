-- 011_money_loop_experiments.sql
-- Persistent experiment + attribution ledger for the proof-first money loop.

CREATE TABLE IF NOT EXISTS buffer_blaster.experiments (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  campaign_id text REFERENCES buffer_blaster.campaigns(id) ON DELETE SET NULL,
  name text NOT NULL,
  hypothesis text NOT NULL,
  primary_kpi text NOT NULL,
  baseline numeric,
  pass_threshold numeric NOT NULL,
  kill_threshold numeric,
  attribution_window_hours integer NOT NULL DEFAULT 168 CHECK (attribution_window_hours > 0),
  budget_ceiling_cents integer NOT NULL DEFAULT 0 CHECK (budget_ceiling_cents >= 0),
  state text NOT NULL DEFAULT 'draft',
  winner_variant_id text,
  decision jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.experiment_variants (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  experiment_id text NOT NULL REFERENCES buffer_blaster.experiments(id) ON DELETE CASCADE,
  content_item_id text REFERENCES buffer_blaster.content_items(id) ON DELETE SET NULL,
  role text NOT NULL CHECK (role IN ('control','variant')),
  label text NOT NULL,
  hypothesis_delta text NOT NULL DEFAULT '',
  external_ad_refs jsonb NOT NULL DEFAULT '{}'::jsonb,
  state text NOT NULL DEFAULT 'draft',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.attribution_events (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  experiment_id text REFERENCES buffer_blaster.experiments(id) ON DELETE CASCADE,
  variant_id text REFERENCES buffer_blaster.experiment_variants(id) ON DELETE SET NULL,
  source text NOT NULL,
  event_type text NOT NULL,
  external_event_id text,
  revenue_cents integer,
  order_ref text,
  occurred_at timestamptz NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source, external_event_id)
);

CREATE TABLE IF NOT EXISTS buffer_blaster.money_loop_receipts (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  experiment_id text REFERENCES buffer_blaster.experiments(id) ON DELETE SET NULL,
  stage text NOT NULL,
  status text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE buffer_blaster.experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.experiment_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.attribution_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.money_loop_receipts ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_experiment_variants_experiment ON buffer_blaster.experiment_variants(experiment_id);
CREATE INDEX IF NOT EXISTS idx_attribution_experiment ON buffer_blaster.attribution_events(experiment_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_money_loop_receipts_experiment ON buffer_blaster.money_loop_receipts(experiment_id, created_at DESC);
