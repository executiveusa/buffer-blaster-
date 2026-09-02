# Supabase CONTEXT

## Inputs
- Ordered SQL under `migrations/`
- Runtime workspace ID and service-role credentials from the private environment

## Job
Provide the canonical persistent state boundary for Buffer Blaster. Production uses the self-hosted Supabase/Postgres stack and schema `buffer_blaster`.

## Outputs
- workspace-scoped tables
- RLS and explicit grants
- additive, repeatable migrations
- durable experiment, attribution, content, and receipt state

## Human check
Apply migrations with `ON_ERROR_STOP`, run them twice in a clean proof environment, verify RLS on every application table, confirm anon/authenticated do not gain unintended direct table access, and never print service-role credentials.
