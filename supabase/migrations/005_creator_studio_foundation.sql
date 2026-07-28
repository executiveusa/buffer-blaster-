begin;

create schema if not exists creator_studio;

revoke all on schema creator_studio from public;
grant usage on schema creator_studio to authenticated, service_role;

create or replace function creator_studio.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = creator_studio, pg_temp
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

revoke all on function creator_studio.set_updated_at() from public, anon, authenticated;
grant execute on function creator_studio.set_updated_at() to service_role;

create table creator_studio.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table creator_studio.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  customer_email text,
  stripe_customer_id text,
  stripe_checkout_session_id text not null unique,
  stripe_payment_intent_id text unique,
  offer_code text not null default 'founding-creator',
  amount_paid integer not null check (amount_paid >= 0),
  currency text not null default 'usd' check (currency ~ '^[a-z]{3}$'),
  status text not null check (status in ('pending', 'paid', 'refunded', 'partially_refunded', 'failed', 'cancelled')),
  purchased_at timestamptz,
  refunded_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table creator_studio.entitlements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  entitlement_code text not null,
  source_purchase_id uuid references creator_studio.purchases(id) on delete set null,
  status text not null default 'active' check (status in ('active', 'revoked', 'expired')),
  granted_at timestamptz not null default timezone('utc', now()),
  revoked_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, entitlement_code)
);

create table creator_studio.stripe_events (
  stripe_event_id text primary key,
  event_type text not null,
  processing_status text not null default 'received' check (processing_status in ('received', 'processing', 'processed', 'failed', 'ignored')),
  payload jsonb not null,
  error_message text,
  received_at timestamptz not null default timezone('utc', now()),
  processed_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table creator_studio.saved_adaptations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  card_id text not null,
  title text not null,
  inputs jsonb not null default '{}'::jsonb,
  adapted_prompt text not null,
  user_edited_prompt text,
  source_hash text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table creator_studio.collections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, name)
);

create table creator_studio.collection_items (
  collection_id uuid not null references creator_studio.collections(id) on delete cascade,
  adaptation_id uuid not null references creator_studio.saved_adaptations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now()),
  primary key (collection_id, adaptation_id)
);

create table creator_studio.export_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  adaptation_id uuid references creator_studio.saved_adaptations(id) on delete set null,
  sha256 text not null,
  object_path text,
  created_at timestamptz not null default timezone('utc', now()),
  expires_at timestamptz
);

create table creator_studio.audit_log (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text,
  entity_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index creator_studio_purchases_user_idx on creator_studio.purchases(user_id, created_at desc);
create index creator_studio_purchases_status_idx on creator_studio.purchases(status, created_at desc);
create index creator_studio_entitlements_user_status_idx on creator_studio.entitlements(user_id, status);
create index creator_studio_stripe_events_status_idx on creator_studio.stripe_events(processing_status, received_at);
create index creator_studio_adaptations_user_updated_idx on creator_studio.saved_adaptations(user_id, updated_at desc);
create index creator_studio_collection_items_user_idx on creator_studio.collection_items(user_id, created_at desc);
create index creator_studio_export_user_created_idx on creator_studio.export_history(user_id, created_at desc);
create index creator_studio_audit_user_created_idx on creator_studio.audit_log(user_id, created_at desc);

create trigger creator_studio_profiles_updated_at before update on creator_studio.profiles
for each row execute function creator_studio.set_updated_at();
create trigger creator_studio_purchases_updated_at before update on creator_studio.purchases
for each row execute function creator_studio.set_updated_at();
create trigger creator_studio_entitlements_updated_at before update on creator_studio.entitlements
for each row execute function creator_studio.set_updated_at();
create trigger creator_studio_stripe_events_updated_at before update on creator_studio.stripe_events
for each row execute function creator_studio.set_updated_at();
create trigger creator_studio_adaptations_updated_at before update on creator_studio.saved_adaptations
for each row execute function creator_studio.set_updated_at();
create trigger creator_studio_collections_updated_at before update on creator_studio.collections
for each row execute function creator_studio.set_updated_at();

alter table creator_studio.profiles enable row level security;
alter table creator_studio.profiles force row level security;
alter table creator_studio.purchases enable row level security;
alter table creator_studio.purchases force row level security;
alter table creator_studio.entitlements enable row level security;
alter table creator_studio.entitlements force row level security;
alter table creator_studio.stripe_events enable row level security;
alter table creator_studio.stripe_events force row level security;
alter table creator_studio.saved_adaptations enable row level security;
alter table creator_studio.saved_adaptations force row level security;
alter table creator_studio.collections enable row level security;
alter table creator_studio.collections force row level security;
alter table creator_studio.collection_items enable row level security;
alter table creator_studio.collection_items force row level security;
alter table creator_studio.export_history enable row level security;
alter table creator_studio.export_history force row level security;
alter table creator_studio.audit_log enable row level security;
alter table creator_studio.audit_log force row level security;

create policy "users read own profile" on creator_studio.profiles
for select to authenticated using (user_id = (select auth.uid()));
create policy "users create own profile" on creator_studio.profiles
for insert to authenticated with check (user_id = (select auth.uid()));
create policy "users update own profile" on creator_studio.profiles
for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "users delete own profile" on creator_studio.profiles
for delete to authenticated using (user_id = (select auth.uid()));

create policy "users read own purchases" on creator_studio.purchases
for select to authenticated using (user_id = (select auth.uid()));

create policy "users read own entitlements" on creator_studio.entitlements
for select to authenticated using (user_id = (select auth.uid()));

create policy "users read own adaptations" on creator_studio.saved_adaptations
for select to authenticated using (user_id = (select auth.uid()));
create policy "users create own adaptations" on creator_studio.saved_adaptations
for insert to authenticated with check (user_id = (select auth.uid()));
create policy "users update own adaptations" on creator_studio.saved_adaptations
for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "users delete own adaptations" on creator_studio.saved_adaptations
for delete to authenticated using (user_id = (select auth.uid()));

create policy "users read own collections" on creator_studio.collections
for select to authenticated using (user_id = (select auth.uid()));
create policy "users create own collections" on creator_studio.collections
for insert to authenticated with check (user_id = (select auth.uid()));
create policy "users update own collections" on creator_studio.collections
for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "users delete own collections" on creator_studio.collections
for delete to authenticated using (user_id = (select auth.uid()));

create policy "users read own collection items" on creator_studio.collection_items
for select to authenticated using (user_id = (select auth.uid()));
create policy "users create own collection items" on creator_studio.collection_items
for insert to authenticated with check (
  user_id = (select auth.uid())
  and exists (select 1 from creator_studio.collections c where c.id = collection_id and c.user_id = (select auth.uid()))
  and exists (select 1 from creator_studio.saved_adaptations a where a.id = adaptation_id and a.user_id = (select auth.uid()))
);
create policy "users delete own collection items" on creator_studio.collection_items
for delete to authenticated using (user_id = (select auth.uid()));

create policy "users read own exports" on creator_studio.export_history
for select to authenticated using (user_id = (select auth.uid()));
create policy "users create own exports" on creator_studio.export_history
for insert to authenticated with check (user_id = (select auth.uid()));

create policy "users read own audit records" on creator_studio.audit_log
for select to authenticated using (user_id = (select auth.uid()));

revoke all on all tables in schema creator_studio from public, anon;
grant select, insert, update, delete on creator_studio.profiles to authenticated;
grant select on creator_studio.purchases to authenticated;
grant select on creator_studio.entitlements to authenticated;
grant select, insert, update, delete on creator_studio.saved_adaptations to authenticated;
grant select, insert, update, delete on creator_studio.collections to authenticated;
grant select, insert, delete on creator_studio.collection_items to authenticated;
grant select, insert on creator_studio.export_history to authenticated;
grant select on creator_studio.audit_log to authenticated;
grant usage, select on sequence creator_studio.audit_log_id_seq to service_role;
grant all on all tables in schema creator_studio to service_role;
grant all on all sequences in schema creator_studio to service_role;

insert into platform.app_registry (
  app_slug,
  app_name,
  schema_name,
  repository,
  production_url,
  owner,
  database_provider,
  storage_namespace,
  migration_status,
  last_capacity_check
)
values (
  'creator-studio',
  'Creator Studio',
  'creator_studio',
  'https://github.com/executiveusa/buffer-blaster-',
  'https://stavarai-platform.vercel.app',
  'The Pauli Effect',
  'supabase',
  null,
  'managed_supabase',
  timezone('utc', now())
)
on conflict (app_slug) do update set
  app_name = excluded.app_name,
  schema_name = excluded.schema_name,
  repository = excluded.repository,
  production_url = excluded.production_url,
  owner = excluded.owner,
  database_provider = excluded.database_provider,
  storage_namespace = excluded.storage_namespace,
  migration_status = excluded.migration_status,
  last_capacity_check = excluded.last_capacity_check;

commit;
