# Proposal — wiring-truth-pricing-v2

## Classification

Brownfield **MERGE / REPAIR**. Do not create a second product plane or a second media provider.

## Problem

The current repository has real infrastructure and a real UGC planning/render boundary, but several production surfaces report static or demo state, some operator controls do not persist or perform a real handshake, interface parity has drifted, the UGC factory stops after a single queued clip, and the current $249 offer is not connected to the working Stripe checkout path.

## Outcome

A customer or agent can move through one truthful path:

`paid trial -> product truth -> gated plan -> explicit spend approval -> bounded generation -> durable receipt -> finished asset state -> library -> human publish approval`

The operator sees canonical state rather than invented counts. All chargeable generation is protected by a server-side margin guard.

## In scope

1. Remove or clearly label synthetic production state on Studio surfaces.
2. Repair settings persistence semantics and provider connection testing semantics.
3. Repair pipeline cancel/runtime truth and voice/CLI/plugin drift where bounded.
4. Restrict Fal result fetching to the configured Fal queue origin.
5. Add a deterministic UGC execution coordinator and durable execution receipts without selecting model IDs in code.
6. Add ffmpeg to the production image for trim/frame/stitch operations.
7. Repair the Supabase migration ordering problem without rewriting historical production data.
8. Replace the stale Founding Creator checkout path with a paid-trial/launch checkout contract.
9. Add a pricing/margin contract where included credits cannot authorize provider spend beyond a configured cost wallet.
10. Add gauntlet checks that prove visible production surfaces do not claim hardcoded activity.

## Out of scope for this change

- Copying MaxFusion proprietary code, hosted MCP, credentials, actors, or branding.
- Auto-publishing.
- Guaranteed ROAS or performance claims.
- A new video provider.
- Making premium MaxFusion-parity features appear live before their execution paths exist.

## Revenue rule

The trial is paid. Included credits are a usage allowance, not cash and not an unlimited promise. A render is allowed only when both the customer credit balance and the internal provider-cost wallet can cover the estimated generation cost. The default target is a positive contribution margin even when every included trial credit is consumed.

## Human approval

The user explicitly approved fixing the audit findings and requested a paid-trial pricing strategy. Publishing remains separately approval-gated.