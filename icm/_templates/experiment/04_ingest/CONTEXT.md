# 04_ingest — normalize performance evidence

One job: collect provider results into the canonical performance and attribution ledger.

## Inputs
- Working: ../03_launch/output/launch-receipt.md
- Reference: API money-loop contract at `/api/studio/money-loop/contract`

Do NOT load: raw unrelated provider history or other workspaces.

## Process
1. Pull/read authorized Meta/TikTok performance metrics for the bound ad IDs.
2. Pull/read Shopify conversion/revenue events for the attribution window.
3. Normalize ad metrics into `performance_events` and commerce outcomes into `attribution_events`.
4. Preserve provider event IDs for idempotency and provenance.

## Outputs
- measurement-summary.md → output/

## Human check
Spot-check normalized totals against the provider dashboards for the same IDs and time window before a winner decision is accepted.
