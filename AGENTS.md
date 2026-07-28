# AGENTS.md — Operating Contract for Creator Studio

> Read this before writing code. Orchestrator: GRINIONS™ v1.

## App identity

- App: Creator Studio
- Slug: `creator-studio`
- Purpose: Discover, adapt, save, and export portable creator workflows.
- Owner: The Pauli Effect

## Repository

- GitHub: `https://github.com/executiveusa/buffer-blaster-`
- Default branch: `main`
- Production branch policy: squash-merge only

## Production

- Production URL: `https://stavarai-platform.vercel.app`
- Vercel project: `stavarai-platform`
- Vercel project ID: `prj_n6CJYyzdUmqHNJ8qlSJalVGerUUW`

## Architecture

```text
frontend/      Next.js 16 creator application and public console
api/           FastAPI operational backend
rust_core/     security and runtime primitives
supabase/      migrations and database boundary tests
skills/        reusable creator and agent skills
ops/           reports, receipts, and rollback artifacts
```

The verified global creator-card corpus remains compiled application data. Supabase stores user state, purchases, entitlements, and audit metadata.

## Database

- Supabase organization: `vijmoorafvspfilmhryn`
- Supabase project: `botanic-creations`
- Project ref: `cyxdevcjycmffhmwxojh`
- Region: `us-west-1`
- Database engine: Postgres 17

## Schema namespace

- App schema: `creator_studio`
- Shared schemas used: `auth` for identity and `platform.app_registry` for safe registry metadata
- Forbidden cross-app schemas: `chispa`, `dosa`, and unrelated application tables in `public`

## Tenancy

- Model: single-user
- Tenant key: `user_id`

## Authentication

- Intended V1 method: Supabase magic link or OTP
- Browser credential: publishable key plus authenticated JWT only
- Service-role and database credentials: server-side only

## RLS model

All tables in `creator_studio` have RLS enabled and forced.

Protected tables:

```text
profiles
purchases
entitlements
stripe_events
saved_adaptations
collections
collection_items
export_history
audit_log
```

Required test status:

```text
metadata RLS enabled/forced: PASS
anonymous table grants absent: PASS
cross-app foreign keys absent: PASS
User A own CRUD: PENDING auth integration test
User B cross-user denial: PENDING auth integration test
anonymous API denial: PENDING API integration test
```

## Storage

- Bucket: none for V1
- Export ZIPs: generated on demand, not stored in Postgres
- Future bucket: `creator-studio-private`
- Future namespace: `creator-studio/<user_id>/exports/`

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

Never store secret values in the repository, chat, logs, screenshots, issues, or documentation.

## Deployment

- Frontend: Vercel
- Database: managed Supabase
- Database changes: migration files only
- No database mutation may be described as complete without verification queries and advisor review.

## Backup

Before destructive database changes, create a Supabase backup or schema-specific `pg_dump`.

## Restore

Restore only the `creator_studio` schema, then recreate and verify grants, RLS, functions, triggers, indexes, Auth assumptions, and environment configuration.

## Capacity status

Last checked: 2026-07-25

```text
Database used: approximately 11 MB before Creator Studio foundation
Storage used: 0 bytes in existing app buckets
Auth users: 0 at inspection time
Risk: LOW
```

## Migration trigger status

No capacity migration trigger is active. Begin planning around 70–80% use or earlier if Creator Studio becomes mission critical, needs independent backups, or requires stronger isolation.

## ONE-CLICK MIGRATION HANDOFF

Trigger phrases:

```text
migrate this app
move this to our server
self host this
database space is getting low
export this app
```

When triggered, create or refresh `MIGRATION_HANDOFF.md`, read `docs/MIGRATION.md`, inventory only `creator_studio`, ask the migration placement questions, export only this schema, recreate all security/database objects, verify row counts and denial tests, update environment variables, deploy, and preserve managed Supabase as rollback until owner acceptance.

Secrets may only be read from `E:\THE PAULI FILES\Cosmos_Vault.env` by an execution environment that actually has access to that path. Never ask the owner to paste secret values into chat.

## Working agreement

1. Verify before claiming completion.
2. Tests before implementation where practical.
3. One reversible phase per PR.
4. Squash-merge only; never force-push `main`.
5. No internal codenames, secrets, or architecture details on public surfaces.
6. Every schema change must have migration, rollback, documentation, and security verification.
