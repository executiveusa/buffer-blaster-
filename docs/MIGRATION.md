# Creator Studio Migration

## Current database

- Provider: Supabase managed Postgres
- Project: `botanic-creations`
- Project ref: `cyxdevcjycmffhmwxojh`
- Region: `us-west-1`
- Schema: `creator_studio`
- Auth source: `auth.users`
- Storage: none for Creator Studio V1

## Source of truth

Database changes are committed under `supabase/migrations/`. The initial schema is `005_creator_studio_foundation.sql`.

## Export

Conceptual schema-only application export:

```bash
pg_dump --schema=creator_studio --format=custom "$SOURCE_DATABASE_URL" > creator_studio.dump
```

Export referenced auth identities separately only when the destination requires user migration. Do not include unrelated app schemas.

## Restore

```bash
pg_restore --dbname="$DEST_DATABASE_URL" creator_studio.dump
```

Re-verify grants, RLS, functions, triggers, indexes, Auth assumptions, and server environment variables after restore.

## Environment variable names

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_FOUNDING_PRICE_ID
SITE_URL
```

Never document secret values.

## Verification

- migration applied successfully
- all Creator Studio tables have enabled and forced RLS
- no grants to `anon` or `PUBLIC`
- no cross-app foreign keys except `auth.users`
- registry entry points to `creator_studio`
- Stripe webhook idempotency key is unique
- application login and CRUD tests pass
- production smoke test passes

## Rollback

Before destructive changes, create a project backup or schema export. For Phase 18 rollback, remove the application registry row and drop `creator_studio` only after confirming there is no retained production data:

```sql
begin;
delete from platform.app_registry where app_slug = 'creator-studio';
drop schema creator_studio cascade;
commit;
```

Do not run this rollback after production data exists without exporting the schema first.

## Migration trigger

Begin dedicated-project or self-hosted planning around 70–80% database/storage usage, or earlier if Creator Studio becomes mission critical, requires independent backups, or needs stronger privacy isolation.
