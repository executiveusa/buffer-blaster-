# Phase 4 — Gemini Server Execution Handoff

## Mission

Complete the **self-hosted production activation** of Buffer Blaster using the actual VPS/Supabase state as truth.

You are running on the server. Do not use the managed `botanic-creations` Supabase project as production. The target is the existing self-hosted Supabase/Postgres stack on this server.

## Repository

- Canonical repo: `https://github.com/executiveusa/buffer-blaster-.git`
- Phase branch: `phase/04-production-schema-activation`
- Current production baseline before this phase: `main` at merge commit `0a4b8abdf00fa101be7ff188413c672bbfd4f284`
- Product name: **Buffer Blaster**

Important files:

- `EMERALD_TABLETS.md`
- `AGENTS.md`
- `openspec/project.md`
- `supabase/migrations/007_buffer_blaster_schema.sql`
- `supabase/migrations/011_money_loop_experiments.sql`
- `api/services/money_loop.py`
- `api/services/performance_ingestion.py`
- `api/routers/shopify_webhooks.py`
- `docker-compose.prod.yml`
- `.env.production.example`
- `scripts/selfhost/install.sh`
- `scripts/selfhost/preflight.sh`
- `scripts/selfhost/smoke.sh`
- `ops/selfhost/Caddyfile`

## Non-negotiable rules

1. **Inspect before changing.** The server's running self-hosted database schema is the deployment truth for this phase.
2. **Do not print, paste, commit, or summarize secret values.** Report only whether required variables exist/non-empty.
3. **Do not rotate or replace existing secrets.**
4. **Do not run paid-media activation or spend.** Meta/TikTok credentials may be inspected only for presence, never printed and never used to activate an ad.
5. **Do not register live Shopify webhooks yet.** That belongs to Phase 5 after Phase 4 infrastructure is proven.
6. **No destructive schema changes.** No DROP/TRUNCATE/DELETE. No forced migration if types/contracts differ.
7. **No migration is considered successful until table types, foreign keys, RLS and API read/write behavior are verified after it.**
8. Keep Buffer Blaster separate from Hermes, STARNET, Maxx and other apps on this VPS.
9. Preserve rollback. Before restarting/replacing a running Buffer Blaster deployment, record current image/container IDs, git commit, compose config hash and current health status.
10. If there is ambiguity about which Supabase/Postgres instance is the self-hosted production target, stop and report the candidates. Do not guess.

## Stage A — Identify the actual self-hosted stack

Run read-only discovery first.

Record:

- hostname and OS (no private keys or tokens)
- running Docker containers and compose projects relevant to Supabase, Postgres, Caddy/Coolify and Buffer Blaster
- the Buffer Blaster install directory if it already exists
- currently checked-out Buffer Blaster git commit/branch if installed
- API domain and frontend origin **names only**
- which Postgres container/database backs the self-hosted Supabase instance
- whether Supabase Kong/PostgREST/Auth/Storage are running

Do not expose environment variable values. For env checks output only `present` / `missing`.

## Stage B — Capture self-hosted Buffer Blaster schema truth

Use the server-side Postgres connection/container to produce a read-only schema report for schema `buffer_blaster`.

At minimum capture:

- all tables
- each table's columns and PostgreSQL data types
- primary keys
- foreign keys and referenced columns/types
- unique constraints
- indexes
- RLS enabled/disabled per table
- RLS policy names/commands/roles (not policy secrets — there should not be any)
- migration/history table contents that identify which Buffer Blaster migrations were applied

Pay special attention to:

- `workspaces`
- `clients`
- `campaigns`
- `content_items`
- `performance_events`
- `experiments`
- `experiment_variants`
- `attribution_events`
- `money_loop_receipts`

Explicitly report the live types for:

- `campaigns.id`
- `content_items.id`
- `performance_events.id`
- `performance_events.content_item_id`
- the live shape of `performance_events` (`source/metric/value/metadata` versus `provider/metrics/revenue_attribution` or another shape)

## Stage C — Compare live schema with repository contract

Compare the Stage B report against:

- `supabase/migrations/007_buffer_blaster_schema.sql`
- `supabase/migrations/011_money_loop_experiments.sql`
- `api/services/money_loop.py`
- `api/services/performance_ingestion.py`

Produce a discrepancy table with columns:

`object | live contract | repo contract | severity | required repo fix | safe migration action`

Do **not** modify the database in this stage.

Stop here and report `BLOCKED_SCHEMA_CONTRACT` if any migration would create a foreign key using a different type than the referenced production column, or if API code writes columns that do not exist in the live table.

## Stage D — Validate runtime configuration without exposing secrets

For the existing Buffer Blaster deployment or intended `.env.production`, report only presence/missing for:

Core:

- `API_DOMAIN`
- `ALLOWED_ORIGINS`
- `MASTER_ENCRYPTION_KEY`
- `BLASTER_API_KEY`
- `TRIAL_SESSION_SECRET`
- `REDIS_PASSWORD`
- `REDIS_URL`
- `BUFFER_BLASTER_WORKSPACE_ID`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `BUFFER_BLASTER_ASSET_BUCKET`

Money loop (presence only; no use yet):

- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID`
- `META_GRAPH_API_VERSION`
- `TIKTOK_ACCESS_TOKEN`
- `TIKTOK_ADVERTISER_ID`
- `TIKTOK_API_BASE_URL`
- `SHOPIFY_WEBHOOK_SECRET`
- `SHOPIFY_SHOP_DOMAIN`
- `SHOPIFY_ADMIN_ACCESS_TOKEN`
- `SHOPIFY_ADMIN_API_VERSION`

Also confirm that `SUPABASE_URL` resolves to the self-hosted Supabase API, not `*.supabase.co`.

## Stage E — Deployment proof (only after schema contract is reconciled in repo)

Do not execute Stage E until the Phase 4 repo branch contains a schema/API contract that matches Stage B and its CI is green.

Then:

1. Record rollback evidence.
2. Pull the approved Phase 4 commit.
3. Run `docker compose -f docker-compose.prod.yml config`.
4. Build without activating providers.
5. Start/update `redis`, `api`, `money-loop-worker`, and `caddy`.
6. Confirm all health checks.
7. Run `scripts/selfhost/preflight.sh`.
8. Run `scripts/selfhost/smoke.sh` if its prerequisites are satisfied.
9. Verify HTTPS API health through the public API domain.
10. Verify the money-loop worker remains alive for at least one polling cycle without provider mutation.
11. Verify the API uses the self-hosted Supabase URL.
12. Do not mark Meta/TikTok/Shopify `live_verified=true`; that is Phase 5.

## Evidence file

Write a sanitized server report to:

`/tmp/buffer-blaster-phase4-server-report.md`

The report must contain **no secret values** and use this structure:

```md
# Buffer Blaster Phase 4 Server Report

## Identity
- host: ...
- Buffer Blaster install: ...
- git commit: ...
- API domain: ...

## Self-hosted Supabase
- postgres container/service: ...
- Supabase API host: ...
- PostgREST: healthy|unhealthy
- Auth: healthy|unhealthy
- Storage: healthy|unhealthy

## Schema truth
...

## Repo discrepancies
| object | live | repo | severity | required repo fix | safe migration action |
|---|---|---|---|---|---|

## Configuration presence
| variable | state |
|---|---|
| ... | present|missing |

## Existing deployment health
...

## Rollback evidence
...

## Final state
READY_FOR_REPO_RECONCILIATION | BLOCKED_SCHEMA_CONTRACT | READY_FOR_DEPLOYMENT | DEPLOYMENT_VERIFIED

## Required next actions
1. ...
```

## Required response to owner/agent

Return only:

1. final state;
2. sanitized schema discrepancy table;
3. deployment/runtime health summary;
4. exact repo files that must change;
5. path to `/tmp/buffer-blaster-phase4-server-report.md`;
6. any blocking condition.

Do not claim Phase 4 complete until the running API + worker + HTTPS + self-hosted Supabase path are all proven.