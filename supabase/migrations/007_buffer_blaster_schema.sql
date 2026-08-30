-- 007_buffer_blaster_schema.sql
-- Canonical Social Studio production ledger.
-- Additive/idempotent. Service-role writes bypass RLS; no public policies are
-- created here, so anon/authenticated clients cannot read these tables directly.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS buffer_blaster;

CREATE TABLE IF NOT EXISTS buffer_blaster.workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text UNIQUE NOT NULL,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.clients (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  slug text NOT NULL,
  name text NOT NULL,
  brand_memory jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, slug)
);

CREATE TABLE IF NOT EXISTS buffer_blaster.campaigns (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  brand text NOT NULL DEFAULT '',
  objective text NOT NULL DEFAULT '',
  audience text NOT NULL DEFAULT '',
  offer text NOT NULL DEFAULT '',
  state text NOT NULL DEFAULT 'draft',
  plan jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.source_assets (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  kind text NOT NULL,
  source_url text,
  storage_url text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.ugc_characters (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  name text NOT NULL,
  reference_asset_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  rights_receipt jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.creative_jobs (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  campaign_id text REFERENCES buffer_blaster.campaigns(id) ON DELETE SET NULL,
  kind text NOT NULL,
  state text NOT NULL,
  input jsonb NOT NULL DEFAULT '{}'::jsonb,
  output jsonb NOT NULL DEFAULT '{}'::jsonb,
  provider_receipt jsonb NOT NULL DEFAULT '{}'::jsonb,
  estimated_provider_cost_cents integer NOT NULL DEFAULT 0 CHECK (estimated_provider_cost_cents >= 0),
  actual_provider_cost_cents integer CHECK (actual_provider_cost_cents IS NULL OR actual_provider_cost_cents >= 0),
  offer_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.model_runs (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  creative_job_id text NOT NULL REFERENCES buffer_blaster.creative_jobs(id) ON DELETE CASCADE,
  provider text NOT NULL,
  model text,
  request_id text,
  state text NOT NULL,
  input jsonb NOT NULL DEFAULT '{}'::jsonb,
  response jsonb NOT NULL DEFAULT '{}'::jsonb,
  estimated_cost_cents integer NOT NULL DEFAULT 0 CHECK (estimated_cost_cents >= 0),
  actual_cost_cents integer CHECK (actual_cost_cents IS NULL OR actual_cost_cents >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.content_items (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  campaign_id text REFERENCES buffer_blaster.campaigns(id) ON DELETE SET NULL,
  creative_job_id text REFERENCES buffer_blaster.creative_jobs(id) ON DELETE SET NULL,
  kind text NOT NULL,
  state text NOT NULL DEFAULT 'draft',
  content text NOT NULL DEFAULT '',
  media_urls jsonb NOT NULL DEFAULT '[]'::jsonb,
  creative_hypothesis jsonb NOT NULL DEFAULT '{}'::jsonb,
  qa_receipt jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.approvals (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  content_item_id text NOT NULL REFERENCES buffer_blaster.content_items(id) ON DELETE CASCADE,
  state text NOT NULL DEFAULT 'pending',
  approved_by text,
  decision_note text,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.channel_connections (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  provider text NOT NULL,
  external_account_id text,
  display_name text,
  state text NOT NULL DEFAULT 'configured_unverified',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.publish_jobs (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  content_item_id text NOT NULL REFERENCES buffer_blaster.content_items(id) ON DELETE CASCADE,
  approval_id text NOT NULL REFERENCES buffer_blaster.approvals(id) ON DELETE RESTRICT,
  channel_connection_id text REFERENCES buffer_blaster.channel_connections(id) ON DELETE SET NULL,
  state text NOT NULL DEFAULT 'queued',
  scheduled_at timestamptz,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.publish_receipts (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  publish_job_id text NOT NULL REFERENCES buffer_blaster.publish_jobs(id) ON DELETE CASCADE,
  external_id text,
  external_url text,
  state text NOT NULL,
  provider_response jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.performance_events (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  content_item_id text NOT NULL REFERENCES buffer_blaster.content_items(id) ON DELETE CASCADE,
  source text NOT NULL,
  metric text NOT NULL,
  value numeric NOT NULL,
  observed_at timestamptz NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.conversations (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  channel text NOT NULL DEFAULT 'studio',
  subject text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.messages (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  conversation_id text NOT NULL REFERENCES buffer_blaster.conversations(id) ON DELETE CASCADE,
  role text NOT NULL,
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.usage_wallets (
  id text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  customer_ref text,
  offer_id text NOT NULL,
  remaining_ad_credits integer NOT NULL CHECK (remaining_ad_credits >= 0),
  remaining_provider_budget_cents integer NOT NULL CHECK (remaining_provider_budget_cents >= 0),
  expires_at timestamptz,
  state text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS buffer_blaster.checkout_receipts (
  id text PRIMARY KEY,
  workspace_id uuid REFERENCES buffer_blaster.workspaces(id) ON DELETE SET NULL,
  stripe_session_id text UNIQUE,
  customer_ref text,
  offer_id text NOT NULL,
  amount_paid_cents integer NOT NULL CHECK (amount_paid_cents >= 0),
  currency text NOT NULL DEFAULT 'usd',
  state text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE buffer_blaster.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.source_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.ugc_characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.creative_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.model_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.channel_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.publish_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.publish_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.performance_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.usage_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.checkout_receipts ENABLE ROW LEVEL SECURITY;

COMMENT ON SCHEMA buffer_blaster IS 'Canonical proprietary Social Studio state. Service-role only unless explicit policies are added later.';
