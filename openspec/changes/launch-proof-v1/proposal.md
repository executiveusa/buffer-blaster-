# Launch Proof V1

## Mode
Brownfield launch slice on top of UGC Ad Factory V1.

## Outcome
A DTC/Shopify operator can understand the offer in under 30 seconds, build a research-grounded UGC factory plan in the UI, explicitly approve a paid render, and receive an inspectable provider receipt without learning prompt engineering.

## Target
- Buyer: Shopify/DTC brands and small creative agencies that need more testable ads without coordinating creators and editors.
- Operator: one authenticated platform operator.
- Agent: any authenticated MCP client using the same factory contract.

## Commercial value
One launch offer only: **Founding Ad Batch — $249 for three review-ready vertical UGC ads built around three distinct customer pains/angles.** This change publishes positioning and offer copy only. It does not alter Stripe configuration or charge behavior; production payment remains a human gate.

## Constraints
- Public product name remains Social Studio; internal codenames stay internal.
- Reuse the existing Fal provider boundary and UGC Factory planner.
- No new media provider or hardcoded model IDs.
- A render call requires explicit `approved: true`.
- No auto-publish.
- No multi-tenant auth.
- No claims of ad performance or conversion lift without measured customer evidence.
- Keep checkout/payment behavior unchanged in this slice.

## Proof
1. Tests define the factory render approval gate before implementation.
2. REST and MCP expose an approved factory-clip render using the existing provider.
3. The Create UI uses product, audience, pain, mechanism and offer—not raw prompt engineering—as its primary inputs.
4. The UI exposes plan gate state, ICM stage state, provider receipt and publish approval state.
5. Homepage and pricing route smoke verify the launch positioning and single paid offer.
6. Full Python, frontend, security, gauntlet, build, route, and self-host smoke pass.
7. A Vercel preview is reviewable before production merge.

## Rollback
One squash revert. No database migration, auth change, secret mutation, payment mutation or publishing mutation.