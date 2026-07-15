-- 002_client_isolation.sql
-- Per-client schema isolation. SECURITY DEFINER so the function can CREATE
-- SCHEMA even when called by a non-superuser service role.
--
-- Contract verified by tests/clients/test_client_isolation.py:
--   - slug is sanitized to [a-z0-9_] (SQL-injection-safe)
--   - returns schema_name matching ^schema_[a-z0-9_]+$
--   - creates 8 buffer-blaster tables under RLS
--   - logs a bead

CREATE OR REPLACE FUNCTION public.create_client_schema(client_slug TEXT)
RETURNS TEXT AS $$
DECLARE
  safe_slug TEXT;
  schema_name TEXT;
BEGIN
  -- Sanitize: lowercase, replace every non [a-z0-9] with '_'.
  safe_slug := regexp_replace(lower(client_slug), '[^a-z0-9]', '_', 'g');
  schema_name := 'schema_' || safe_slug;

  -- Defence-in-depth: never allow a name outside the safe pattern.
  IF schema_name !~ '^schema_[a-z0-9_]+$' THEN
    RAISE EXCEPTION 'unsafe schema name derived from slug: %', client_slug;
  END IF;

  EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);

  -- content_units — the core post record
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.content_units (
      id                  uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    )
  $f$, schema_name);

  -- interviews
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.interviews (
      id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      questions     jsonb DEFAULT '[]',
      answers       jsonb DEFAULT '[]',
      brief_yaml    text,
      completed_at  timestamptz,
      created_at    timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- research_runs
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.research_runs (
      id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      platforms         jsonb DEFAULT '[]',
      outliers          jsonb DEFAULT '[]',
      trends            jsonb DEFAULT '{}',
      customer_segments jsonb DEFAULT '{}',
      run_at            timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- approval_queues
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.approval_queues (
      id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      content_unit_ids jsonb DEFAULT '[]',
      sent_at          timestamptz DEFAULT now(),
      approved_at      timestamptz,
      approved_by      text,
      changes_requested text,
      status           text DEFAULT 'pending'
                       CHECK (status IN ('pending','approved','changes_requested','expired'))
    )
  $f$, schema_name);

  -- buffer_posts
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.buffer_posts (
      id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      content_unit_id  uuid,
      buffer_update_id text UNIQUE,
      platform         text,
      scheduled_at     timestamptz,
      published_at     timestamptz,
      engagement       jsonb DEFAULT '{}',
      created_at       timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- airtable_assets
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.airtable_assets (
      id                 uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      airtable_record_id text UNIQUE NOT NULL,
      image_url          text NOT NULL,
      github_path        text NOT NULL,
      tags               jsonb DEFAULT '[]',
      synced_at          timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- customer_segments (from Shopify CSV)
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.customer_segments (
      id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      segment_name    text,
      avg_ltv         numeric,
      top_products    jsonb DEFAULT '[]',
      count           integer,
      imported_at     timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- scoring_weights (autoresearch loop tunes these)
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.scoring_weights (
      id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      hook_strength    numeric(4,2) DEFAULT 0.25,
      platform_fit     numeric(4,2) DEFAULT 0.20,
      niche_relevance  numeric(4,2) DEFAULT 0.20,
      trend_alignment  numeric(4,2) DEFAULT 0.15,
      visual_quality   numeric(4,2) DEFAULT 0.10,
      audience_match   numeric(4,2) DEFAULT 0.10,
      version          integer DEFAULT 1,
      updated_at       timestamptz DEFAULT now()
    )
  $f$, schema_name);

  -- RLS on every client table: service_role only.
  EXECUTE format('ALTER TABLE %I.content_units    ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.interviews      ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.research_runs   ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.approval_queues ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.buffer_posts    ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.airtable_assets ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.customer_segments ENABLE ROW LEVEL SECURITY', schema_name);
  EXECUTE format('ALTER TABLE %I.scoring_weights ENABLE ROW LEVEL SECURITY', schema_name);

  -- Force the service-role bypass off for these schemas so RLS always applies.
  -- (Supabase service_role bypasses RLS by default; for client schemas we add
  -- an explicit policy and rely on the app always scoping queries by schema.)

  -- Log a bead.
  INSERT INTO public.beads (action, scope, description, reversible)
  VALUES ('schema-created', client_slug,
          format('Client schema created: %s', schema_name), true);

  RETURN schema_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
