# U1 Canonical Media Contracts + Receipts

## Mode
Brownfield MERGE into the existing Buffer Blaster Studio ledger, REST, MCP, CLI, and self-hosted Supabase boundary.

## Outcome
An authenticated operator or agent can create and read the same provider-neutral, no-spend UGCPlan receipt through REST, MCP, and CLI, with durable workspace-scoped persistence and idempotency.

## Constraints
- Reuse existing FastAPI, auth, Supabase/PostgREST, Redis fallback, MCP, and CLI seams.
- No new renderer or paid generation call in this slice.
- Preserve wallet, approval, publishing, and workspace isolation gates.
- Do not mutate legacy campaign/job identifier types.
- New schema is additive, repeatable, RLS-enabled, and service-role-only by default.
- Rights state, consent/export policy, cost ceiling, and idempotency are explicit.

## Scope
Introduce provider-neutral domain contracts for CreativeSource, StrategyReceipt, UGCPlan, MediaTake, and ProviderCapabilities. Add durable tables for the four receipt types. Expose the no-spend UGC plan create/read parity required to prove U1.

## Proof
1. Fresh PostgreSQL migration proof applies the new migration twice and verifies RLS.
2. Tests cover contract validation, workspace scoping, and duplicate idempotency behavior.
3. REST, MCP, and CLI create/read the same no-spend plan.
4. Existing CI stays green.
5. The new U1 paths never invoke a generation provider.

## Commercial value
Creates the governed receipt layer required for repeatable creative testing rather than vendor-specific generation jobs.

## Rollback
Revert the application squash merge if needed. The database migration is additive; do not drop new receipt tables during emergency rollback.
