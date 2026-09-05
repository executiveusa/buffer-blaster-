# Buffer Blaster remote-agent interoperability

All examples use the same authenticated Buffer Blaster operator boundary. REST, MCP and CLI are alternate transports over the same canonical services; none grant raw provider credentials or browser-owned spend authority.

## 1. Bring Shopify product truth into creative planning

REST: `POST /api/studio/shopify/context`

MCP: `create_shopify_product_context`

CLI: `python -m cli.blaster shopify-context product.json`

Required product context is intentionally small: server-resolved workspace, client id, Shopify shop/product identity, product truth, optional rights-cleared image URLs/variants, and an idempotency key. The receipt contains a stable creative seed and costs zero provider cents.

## 2. Create or inspect creative plans

Canonical no-spend operations include:

- UGC receipt: REST `/api/studio/ugc/plans`, MCP `create_ugc_plan`, CLI `ugc-plan-create`.
- Reference strategy: REST `/api/studio/reference-ads/analyze`, MCP `analyze_reference_ad`, CLI `reference-analyze`.
- Long-form repurpose: REST `/api/studio/repurpose/plans`, MCP `create_repurpose_plan`, CLI `repurpose-plan`.
- Provider dry-run: REST `/api/studio/providers/route`, MCP `plan_provider_route`, CLI `provider-route`.

Readback uses the receipt IDs returned by the create operation. Reusing an idempotency key with materially different input must fail rather than silently overwrite the original receipt.

## 3. Prepare downstream Buffer distribution

Buffer is optional downstream infrastructure, not Buffer Blaster's core scheduler. `GET /api/studio/social/accounts`, MCP `list_social_accounts`, or CLI `accounts` returns configured downstream channels when Buffer is attached.

Actual scheduling remains consequential: REST `/api/studio/social/schedule`, MCP `schedule_social_drop`, and CLI `schedule` require an exact Social Drop with explicit approval. A disabled publisher or missing approval fails closed.

## 4. Read Shopify + paid-media evidence

Shopify financial events enter only through signed `/api/webhooks/shopify/orders` deliveries. `orders/paid` creates positive revenue; successful refund transactions create negative adjustments; lifecycle-only refund/cancel events are not treated as completed cash movement.

Experiment evidence/readback:

- REST: `POST /api/studio/money-loop/experiments/{experiment_id}/sync`
- MCP: `sync_experiment_evidence`
- CLI: `python -m cli.blaster experiment-sync <experiment-id>`

The sync path reads the workspace-scoped experiment, provider metrics and Shopify attribution, then returns normalized variant results and the deterministic PASS/ITERATE/KILL/HOLD evaluation. It does not activate an ad or increase a budget.

## Authentication and sovereignty

- REST/MCP consequential operations require the operator boundary.
- CLI sends `BLASTER_API_KEY` only to the configured Buffer Blaster API base.
- Shopify context derives workspace identity from server configuration; callers cannot select another workspace.
- Provider credentials remain server-side environment/configuration.
- Paid generation still requires a server-owned wallet plus explicit approval.
- Publishing/ad activation remains explicitly gated.
