# Creator Studio Security

## Isolation

Creator Studio owns only `creator_studio.*` and may read/write `platform.app_registry` only through controlled migration or operator workflows. It has no approved access to `chispa.*`, `dosa.*`, or unrelated application tables in `public`.

## Authentication

Supabase Auth is the identity source. The intended V1 login method is magic link or OTP. Browser code may use only a Supabase publishable key and the authenticated user's JWT.

## Privileged secrets

Never expose or commit:

- Supabase service-role keys
- database passwords or connection strings
- Stripe secret keys or webhook secrets
- direct Postgres credentials

Stripe webhook and entitlement mutations must run server-side.

## RLS

All Creator Studio tables have RLS enabled and forced.

User-managed tables allow authenticated users to operate only on rows where:

```sql
user_id = (select auth.uid())
```

`purchases` and `entitlements` are client read-only. `stripe_events` has no browser policy or browser table grant. `audit_log` is client read-only for the current user's rows.

## Required boundary tests

- own read/insert/update/delete for profiles, adaptations, and collections
- cross-user reads and writes denied
- inserting another user's `user_id` denied
- anonymous access denied
- no cross-app foreign keys except the approved `auth.users` identity reference
- no grants to `anon` or `PUBLIC`

The repository metadata assertions live in `supabase/tests/creator_studio_security.sql`. Full User A/User B JWT integration tests must run when Supabase Auth is wired into the application.

## Stripe

- Verify Stripe webhook signatures before reading an event.
- Insert `stripe_event_id` before processing to enforce idempotency.
- Never grant access based only on a success-page redirect.
- Purchase and entitlement writes require a trusted server identity.
- Refund and entitlement-revocation actions must be audited.
