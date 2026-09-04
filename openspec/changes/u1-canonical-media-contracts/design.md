# Design — U1 Canonical Media Contracts

## Existing seams reused
- Authenticated REST: `api/routers/studio.py`
- MCP JSON-RPC: `api/routers/mcp.py`
- CLI: `cli/blaster.py`
- Canonical ledger conventions: `api/services/studio_ledger.py`
- Self-hosted schema: `buffer_blaster`
- PostgREST service-role access: migration `012_selfhost_postgrest_access.sql`

## Domain contracts
`api/services/media_contracts.py` owns provider-neutral Pydantic contracts and validation for CreativeSource, StrategyReceipt, UGCPlan, MediaTake, and ProviderCapabilities.

The contracts carry receipt IDs, workspace lineage, rights/consent state, provider-export policy, cost ceilings, provenance, and immutable take relationships without selecting a renderer.

## Persistence service
`api/services/media_receipts.py` provides workspace-scoped create/read persistence using self-hosted Supabase when configured and the existing Redis topology as a truthful degraded fallback. It never fabricates successful persistence when neither backend exists.

UGC plan creation uses `(workspace_id, idempotency_key)` as the idempotency boundary. Repeating the same key returns the existing plan instead of creating a second receipt.

## Schema
Add migration `013_ugc_canonical_receipts.sql` with four additive tables:
- `creative_sources`
- `strategy_receipts`
- `ugc_plans`
- `media_takes`

All tables use UUID primary keys, UUID workspace foreign keys, RLS, timestamps, and explicit checks for bounded cost/duration and normalized enum-like states. `ugc_plans` has a unique `(workspace_id, idempotency_key)` constraint. Legacy campaign/job IDs are unchanged.

## Interface parity
REST:
- `POST /api/studio/ugc/plans`
- `GET /api/studio/ugc/plans/{plan_id}`

MCP:
- `create_ugc_plan`
- `get_ugc_plan`

CLI:
- `ugc-plan-create <json>`
- `ugc-plan-get <plan-id>`

All three call the same canonical service. These are planning/receipt paths only and never invoke `get_media_provider`, reserve a wallet, or submit provider jobs.

## Security and rights boundary
Plan inputs must include a non-negative estimated cost ceiling, explicit approval state, rights/consent references as applicable, and a stable idempotency key. Source contracts make owner/rights state and provider export permission explicit. Person/voice source kinds require an explicit consent state.

## Blast radius
Additive migration plus one contract module, one receipt service, small REST/MCP/CLI route additions, tests, and rollback receipt. No frontend, provider, wallet, publishing, or deployment change.
