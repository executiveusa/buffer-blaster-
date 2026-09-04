-- 013_ugc_canonical_receipts.sql
-- Provider-neutral UGC source/strategy/plan/take receipts.
-- Additive and idempotent. RLS is enabled with no public policies; migration
-- 012 default privileges keep backend service-role access for future tables.

CREATE TABLE IF NOT EXISTS buffer_blaster.creative_sources (
  source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  kind text NOT NULL CHECK (kind IN ('product_image','creator_image','reference_ad','source_video','source_audio','brand_asset','url')),
  uri text,
  storage_key text,
  sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-fA-F]{64}$'),
  mime_type text NOT NULL,
  owner text NOT NULL,
  rights_state text NOT NULL CHECK (rights_state IN ('owned','licensed','authorized_analysis','restricted','unknown')),
  consent_state text NOT NULL DEFAULT 'not_applicable' CHECK (consent_state IN ('not_applicable','pending','granted','denied')),
  provider_export_allowed boolean NOT NULL DEFAULT false,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (uri IS NOT NULL OR storage_key IS NOT NULL),
  CHECK (NOT provider_export_allowed OR consent_state <> 'denied')
);

CREATE TABLE IF NOT EXISTS buffer_blaster.strategy_receipts (
  receipt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_hashes jsonb NOT NULL DEFAULT '[]'::jsonb,
  hook_mechanic text NOT NULL DEFAULT '',
  angle text NOT NULL DEFAULT '',
  customer_tension text NOT NULL DEFAULT '',
  narrative_structure text NOT NULL DEFAULT '',
  pacing text NOT NULL DEFAULT '',
  creator_archetype text NOT NULL DEFAULT '',
  proof_device text NOT NULL DEFAULT '',
  shot_logic jsonb NOT NULL DEFAULT '[]'::jsonb,
  cta_mechanic text NOT NULL DEFAULT '',
  claims_brand_risks jsonb NOT NULL DEFAULT '[]'::jsonb,
  originality_transformations jsonb NOT NULL DEFAULT '[]'::jsonb,
  recommended_test_variable text NOT NULL DEFAULT '',
  model_provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(source_refs) = 'array'),
  CHECK (jsonb_array_length(source_refs) > 0)
);

CREATE TABLE IF NOT EXISTS buffer_blaster.ugc_plans (
  plan_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  client_id uuid REFERENCES buffer_blaster.clients(id) ON DELETE SET NULL,
  product_source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  creator_source_ref uuid REFERENCES buffer_blaster.creative_sources(source_id) ON DELETE SET NULL,
  setting_style_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  strategy_receipt_ref uuid REFERENCES buffer_blaster.strategy_receipts(receipt_id) ON DELETE SET NULL,
  script text NOT NULL,
  shot_plan jsonb NOT NULL DEFAULT '[]'::jsonb,
  aspect_ratio text NOT NULL DEFAULT '9:16' CHECK (aspect_ratio IN ('9:16','16:9','1:1','4:5')),
  duration_seconds integer NOT NULL DEFAULT 10 CHECK (duration_seconds BETWEEN 1 AND 300),
  finish_mode text NOT NULL DEFAULT 'raw_ugc' CHECK (finish_mode IN ('raw_ugc','creator_premium','product_cinematic','editorial_brand')),
  provider_preference text NOT NULL DEFAULT 'auto' CHECK (provider_preference IN ('auto','fast','premium','sovereign')),
  estimated_cost_ceiling_cents integer NOT NULL CHECK (estimated_cost_ceiling_cents >= 0),
  approval_state text NOT NULL DEFAULT 'draft' CHECK (approval_state IN ('draft','pending','approved','rejected')),
  consent_rights_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 128),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, idempotency_key),
  CHECK (jsonb_typeof(product_source_refs) = 'array'),
  CHECK (jsonb_array_length(product_source_refs) > 0),
  CHECK (jsonb_typeof(shot_plan) = 'array'),
  CHECK (jsonb_array_length(shot_plan) > 0),
  CHECK (creator_source_ref IS NULL OR jsonb_array_length(consent_rights_refs) > 0)
);

CREATE TABLE IF NOT EXISTS buffer_blaster.media_takes (
  take_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES buffer_blaster.ugc_plans(plan_id) ON DELETE CASCADE,
  parent_take_id uuid REFERENCES buffer_blaster.media_takes(take_id) ON DELETE SET NULL,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  provider text NOT NULL,
  model_name text NOT NULL,
  model_version text,
  request_job_id text,
  actual_cost_cents integer NOT NULL DEFAULT 0 CHECK (actual_cost_cents >= 0),
  output_storage_key text,
  artifact_hash text CHECK (artifact_hash IS NULL OR artifact_hash ~ '^[0-9a-fA-F]{64}$'),
  width integer CHECK (width IS NULL OR width > 0),
  height integer CHECK (height IS NULL OR height > 0),
  duration_seconds numeric CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
  derivation_state text NOT NULL DEFAULT 'generated' CHECK (derivation_state IN ('generated','derived')),
  finish_state text NOT NULL DEFAULT 'raw' CHECK (finish_state IN ('raw','processing','finished','failed')),
  provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS creative_sources_workspace_created_idx
  ON buffer_blaster.creative_sources (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS strategy_receipts_workspace_created_idx
  ON buffer_blaster.strategy_receipts (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ugc_plans_workspace_created_idx
  ON buffer_blaster.ugc_plans (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS media_takes_plan_created_idx
  ON buffer_blaster.media_takes (plan_id, created_at DESC);

ALTER TABLE buffer_blaster.creative_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.strategy_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.ugc_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE buffer_blaster.media_takes ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE buffer_blaster.creative_sources IS 'Canonical rights-aware media/evidence entering Buffer Blaster.';
COMMENT ON TABLE buffer_blaster.strategy_receipts IS 'Provider-neutral creative strategy analysis receipt.';
COMMENT ON TABLE buffer_blaster.ugc_plans IS 'Provider-neutral no-spend plan and approval/cost boundary before generation.';
COMMENT ON TABLE buffer_blaster.media_takes IS 'Immutable generated or derived media take lineage; takes never overwrite one another.';
