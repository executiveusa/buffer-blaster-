# Creator Studio Data Model

## Database

- Provider: Supabase managed Postgres
- Project: `botanic-creations`
- Project ref: `cyxdevcjycmffhmwxojh`
- Region: `us-west-1`
- App schema: `creator_studio`
- Shared schema used: `platform.app_registry` only
- Forbidden cross-app schemas: `chispa`, `dosa`, and unrelated `public` application tables

## Tenancy

Creator Studio V1 is single-user tenancy. Every private user-owned row carries `user_id`, referencing `auth.users(id)`.

## Tables

- `profiles`: Creator Studio preferences and display metadata.
- `purchases`: Server-managed Stripe purchase records. Clients have read-only access to their own rows.
- `entitlements`: Server-managed access grants. Clients have read-only access to their own rows.
- `stripe_events`: Private idempotency and webhook-processing ledger. No browser role has access.
- `saved_adaptations`: User-owned adapted and edited prompts.
- `collections`: User-owned organization containers.
- `collection_items`: Joins owned collections to owned adaptations.
- `export_history`: Export receipts and hashes. ZIP binaries are not stored in Postgres.
- `audit_log`: Server-written audit records; users may read only their own records.

## Storage

No Creator Studio bucket is created in V1. Exports are generated on demand. If temporary cloud exports are introduced later, use a private `creator-studio-private` bucket with paths scoped to `creator-studio/<user_id>/exports/` and an expiration policy.

## Corpus boundary

The verified global creator-card corpus remains compiled application data. Supabase stores user state and commerce records, not duplicate copies of the global corpus.
