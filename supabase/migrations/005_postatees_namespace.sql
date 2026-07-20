-- 005_postatees_namespace.sql
-- Isolation fix: the existing public.* schema is occupied by cascadia-brain
-- (different clients table, different columns, different constraints).
-- We move ALL Postatees Stavarai Platform tables under a dedicated schema so
-- there is zero collision with other apps on the shared Supabase instance.
--
-- Safe to re-run (IF NOT EXISTS everywhere).

CREATE SCHEMA IF NOT EXISTS postatees_stavarai;

-- Move the extension (no-op if already public)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── clients (our shape, not cascadia's) ──────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.clients (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug        text UNIQUE NOT NULL,
  name        text NOT NULL,
  niche       text NOT NULL CHECK (niche IN ('food-beverage','beauty-skincare','apparel','home-lifestyle')),
  shopify_url text,
  schema_name text,
  status      text DEFAULT 'active',
  posts_scheduled integer DEFAULT 0,
  avg_score   numeric DEFAULT 0.0,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- ── interviews ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.interviews (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id     uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  questions     jsonb DEFAULT '[]',
  answers       jsonb DEFAULT '[]',
  brief_yaml    text,
  completed_at  timestamptz,
  created_at    timestamptz DEFAULT now()
);

-- ── research_runs ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.research_runs (
  id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id         uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  platforms         jsonb DEFAULT '[]',
  outliers          jsonb DEFAULT '[]',
  trends            jsonb DEFAULT '{}',
  customer_segments jsonb DEFAULT '{}',
  run_at            timestamptz DEFAULT now()
);

-- ── content_units ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.content_units (
  id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id           uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  type                text NOT NULL CHECK (type IN ('video','image','carousel','text')),
  platform            text NOT NULL,
  hook                text,
  caption             text,
  caption_variants    jsonb DEFAULT '[]',
  video_prompt        text,
  video_url           text,
  image_urls          jsonb DEFAULT '[]',
  raw_score           integer CHECK (raw_score BETWEEN 0 AND 100),
  score_breakdown     jsonb DEFAULT '{}',
  status              text DEFAULT 'draft'
                      CHECK (status IN ('draft','scored','queued','approved','published','rejected')),
  scheduled_at        timestamptz,
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now()
);

-- ── approval_queues ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.approval_queues (
  id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id         uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  content_unit_ids  jsonb DEFAULT '[]',
  sent_at           timestamptz DEFAULT now(),
  approved_at       timestamptz,
  approved_by       text,
  changes_requested text,
  status            text DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','changes_requested','expired'))
);

-- ── buffer_posts ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.buffer_posts (
  id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id         uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  content_unit_id   uuid,
  buffer_update_id  text UNIQUE,
  platform          text,
  scheduled_at      timestamptz,
  published_at      timestamptz,
  engagement        jsonb DEFAULT '{}',
  created_at        timestamptz DEFAULT now()
);

-- ── airtable_assets ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.airtable_assets (
  id                 uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id          uuid REFERENCES postatees_stavarai.clients(id),
  airtable_record_id text UNIQUE NOT NULL,
  image_url          text NOT NULL,
  github_path        text NOT NULL,
  tags               jsonb DEFAULT '[]',
  synced_at          timestamptz DEFAULT now()
);

-- ── beads ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.beads (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  timestamp    timestamptz DEFAULT now(),
  action       text NOT NULL,
  scope        text,
  agent        text,
  reversible   boolean DEFAULT true,
  description  text,
  artifacts    jsonb DEFAULT '[]',
  notes        text
);

-- ── agent_logs ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.agent_logs (
  id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id  uuid REFERENCES postatees_stavarai.clients(id),
  agent_name text,
  phase      text,
  level      text DEFAULT 'info',
  message    text,
  metadata   jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- ── scoring_weights ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postatees_stavarai.scoring_weights (
  id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id        uuid REFERENCES postatees_stavarai.clients(id) ON DELETE CASCADE,
  hook_strength    numeric(4,2) DEFAULT 0.25,
  platform_fit     numeric(4,2) DEFAULT 0.20,
  niche_relevance  numeric(4,2) DEFAULT 0.20,
  trend_alignment  numeric(4,2) DEFAULT 0.15,
  visual_quality   numeric(4,2) DEFAULT 0.10,
  audience_match   numeric(4,2) DEFAULT 0.10,
  version          integer DEFAULT 1,
  updated_at       timestamptz DEFAULT now()
);

-- ── blog_posts (only if not already in public) ───────────────
-- This one we may have created in 004. Create here under our schema too.
CREATE TABLE IF NOT EXISTS postatees_stavarai.blog_posts (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug         text UNIQUE NOT NULL,
  title        text NOT NULL,
  excerpt      text,
  content      text,
  category     text,
  published    boolean DEFAULT false,
  published_at timestamptz,
  reading_time int,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- ── Update create_client_schema to live in our namespace ─────
-- The original 002 function creates schema_{slug} at the top level.
-- We add a Postatees-aware variant that namespaces per-client schemas
-- under postatees_stavarai (e.g. postatees_stavarai.schema_cella_coffee).
-- This keeps every Postatees client schema visually grouped + isolated
-- from any other app that might use top-level schema_* names.

CREATE OR REPLACE FUNCTION postatees_stavarai.create_client_schema(client_slug TEXT)
RETURNS TEXT AS $$
DECLARE
  safe_slug TEXT;
  schema_name TEXT;
BEGIN
  safe_slug := regexp_replace(lower(client_slug), '[^a-z0-9]', '_', 'g');
  schema_name := 'postatees_stavarai.schema_' || safe_slug;

  IF schema_name !~ '^postatees_stavarai\.schema_[a-z0-9_]+$' THEN
    RAISE EXCEPTION 'unsafe schema name derived from slug: %', client_slug;
  END IF;

  EXECUTE format('CREATE SCHEMA IF NOT EXISTS %s', schema_name);
  -- Per-client tables would be created here in a fuller impl.
  -- For now we just reserve the namespace and log it.

  INSERT INTO postatees_stavarai.beads (action, scope, description, reversible)
  VALUES ('schema-created', client_slug,
          format('Postatees client schema created: %s', schema_name), true);

  RETURN schema_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── Seed the demo clients INTO OUR SCHEMA (not public) ───────
INSERT INTO postatees_stavarai.clients (slug, name, niche, shopify_url, schema_name, status, posts_scheduled, avg_score)
VALUES
  ('cella-coffee', 'Cella Coffee Roasters', 'food-beverage',
   'https://cella-coffee.myshopify.com', 'postatees_stavarai.schema_cella_coffee',
   'active', 47, 84.2),
  ('lumen-skincare', 'Lumen Skincare', 'beauty-skincare',
   'https://lumen-skincare.myshopify.com', 'postatees_stavarai.schema_lumen_skincare',
   'active', 31, 86.7)
ON CONFLICT (slug) DO NOTHING;

-- ── Bead ─────────────────────────────────────────────────────
INSERT INTO postatees_stavarai.beads (action, scope, description, reversible)
VALUES ('postatees-namespace-created', 'postatees_stavarai',
        'Dedicated postatees_stavarai schema created — full isolation from public.*',
        true);
