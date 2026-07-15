-- Buffer Blaster — Initial Schema
-- Run via: supabase db push

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ── clients ──────────────────────────────────────────────────────────────────
create table if not exists clients (
  id              uuid primary key default uuid_generate_v4(),
  slug            text unique not null,
  name            text not null,
  niche           text not null check (niche in ('food-beverage','beauty-skincare','apparel','home-lifestyle')),
  shopify_url     text,
  airtable_gallery_url text,
  buffer_profile_ids  jsonb default '[]'::jsonb,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ── interviews ───────────────────────────────────────────────────────────────
create table if not exists interviews (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  questions_json  jsonb default '[]'::jsonb,
  answers_json    jsonb default '[]'::jsonb,
  brief_yaml      text,
  completed_at    timestamptz,
  created_at      timestamptz default now()
);

-- ── research_runs ─────────────────────────────────────────────────────────────
create table if not exists research_runs (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  platforms_json  jsonb default '[]'::jsonb,
  outliers_json   jsonb default '[]'::jsonb,
  trends_json     jsonb default '{}'::jsonb,
  customer_segments_json jsonb default '{}'::jsonb,
  run_at          timestamptz default now()
);

-- ── content_units ─────────────────────────────────────────────────────────────
create table if not exists content_units (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  research_run_id uuid references research_runs(id),
  type            text not null check (type in ('video','image','carousel','text')),
  platform        text not null,
  hook            text,
  caption         text,
  caption_variants jsonb default '[]'::jsonb,
  video_prompt    text,
  video_url       text,
  image_urls      jsonb default '[]'::jsonb,
  raw_score       integer check (raw_score between 0 and 100),
  score_breakdown_json jsonb default '{}'::jsonb,
  status          text default 'draft' check (status in ('draft','scored','queued','approved','published','rejected')),
  scheduled_at    timestamptz,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ── approval_queues ──────────────────────────────────────────────────────────
create table if not exists approval_queues (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  content_unit_ids jsonb default '[]'::jsonb,
  sent_at         timestamptz default now(),
  approved_at     timestamptz,
  approved_by     text,
  changes_requested text,
  status          text default 'pending' check (status in ('pending','approved','changes_requested','expired'))
);

-- ── buffer_posts ─────────────────────────────────────────────────────────────
create table if not exists buffer_posts (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  content_unit_id uuid references content_units(id),
  buffer_update_id text unique,
  platform        text,
  scheduled_at    timestamptz,
  published_at    timestamptz,
  engagement_json jsonb default '{}'::jsonb,
  created_at      timestamptz default now()
);

-- ── airtable_assets ──────────────────────────────────────────────────────────
create table if not exists airtable_assets (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id),
  airtable_record_id text unique not null,
  image_url       text not null,
  github_path     text not null,
  tags_json       jsonb default '[]'::jsonb,
  synced_at       timestamptz default now()
);

-- ── beads (change log) ──────────────────────────────────────────────────────
create table if not exists beads (
  id              uuid primary key default uuid_generate_v4(),
  timestamp       timestamptz default now(),
  action          text not null,
  file_path       text,
  diff_hash       text,
  reversible      boolean default true,
  notes           text
);

-- ── agent_logs ───────────────────────────────────────────────────────────────
create table if not exists agent_logs (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id),
  agent_name      text,
  phase           text,
  level           text default 'info',
  message         text,
  metadata_json   jsonb default '{}'::jsonb,
  created_at      timestamptz default now()
);

-- ── scoring_weights (per client, evolves over time) ─────────────────────────
create table if not exists scoring_weights (
  id              uuid primary key default uuid_generate_v4(),
  client_id       uuid references clients(id) on delete cascade,
  hook_strength   numeric(4,2) default 0.25,
  platform_fit    numeric(4,2) default 0.20,
  niche_relevance numeric(4,2) default 0.20,
  trend_alignment numeric(4,2) default 0.15,
  visual_quality  numeric(4,2) default 0.10,
  audience_match  numeric(4,2) default 0.10,
  updated_at      timestamptz default now(),
  version         integer default 1
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
create index if not exists idx_content_units_client_status on content_units(client_id, status);
create index if not exists idx_content_units_score on content_units(raw_score desc);
create index if not exists idx_buffer_posts_client on buffer_posts(client_id, scheduled_at);
create index if not exists idx_agent_logs_client_phase on agent_logs(client_id, phase, created_at);

-- ── RLS (Row Level Security) — enable for production ─────────────────────────
alter table clients enable row level security;
alter table content_units enable row level security;
alter table approval_queues enable row level security;
alter table buffer_posts enable row level security;

-- Service role bypass (agent uses service key)
create policy "service_role_all" on clients for all using (auth.role() = 'service_role');
create policy "service_role_all" on content_units for all using (auth.role() = 'service_role');
create policy "service_role_all" on approval_queues for all using (auth.role() = 'service_role');
create policy "service_role_all" on buffer_posts for all using (auth.role() = 'service_role');

-- ── Updated_at trigger ────────────────────────────────────────────────────────
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger clients_updated_at before update on clients
  for each row execute function update_updated_at();

create trigger content_units_updated_at before update on content_units
  for each row execute function update_updated_at();
