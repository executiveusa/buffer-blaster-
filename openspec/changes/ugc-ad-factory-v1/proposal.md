# UGC Ad Factory V1

## Mode
Brownfield MERGE into the existing Buffer Blaster UGC, media, MCP, and ICM surfaces.

## Outcome
An authenticated agent can submit one structured product brief and receive a deterministic, gated two-clip UGC production plan that is ready for the existing media provider boundary, including continuity instructions and a configurable commercial quote.

## Target
- Primary: agents using `/api/mcp`
- Secondary: operators using `/api/studio/*`
- Buyer: Shopify/e-commerce brands purchasing finished short-form UGC ads

## Constraints
- Reuse `api/services/media_generation.py`; do not add a second video provider.
- Keep model/provider IDs environment-driven.
- No MaxFusion runtime dependency, credentials, branding, or proprietary API calls.
- No auto-publishing and no payment behavior changes.
- Preserve client isolation, auth, and current public app boundaries.
- Keep this slice dry-run safe: planning and validation must work without paid media calls.

## Open-source inputs
This change adapts workflow patterns, not hosted MaxFusion services:
- MaxFusion AI `OMNI-UGC-AD-FACTORY` (MIT): structured prompt gates, two-clip continuity, seam-QA ordering, natural-speech constraints.
- Existing Buffer Blaster `skills/ugc-video` source material: platform/niche UGC prompting patterns.

MIT attribution is preserved in documentation where applicable.

## Proof
1. Tests demonstrate factory plan shape, script gates, continuity order, ICM contract, and agent/MCP exposure.
2. Existing full Python test suite passes.
3. PR CI passes without requiring FAL or other paid-generation secrets.
4. MCP exposes `create_ugc_ad_factory_plan`.
5. REST exposes `/api/studio/ugc/factory/plan` behind existing operator auth.

## Commercial value
Turn one product brief into a repeatable billable unit: one finished UGC ad package. The planner returns configurable retail price, estimated production cost, and gross-margin estimate before generation. This is quoting metadata only; it does not charge customers.

## Rollback
Revert the single squash merge for this OpenSpec change. No database migration, secret mutation, deployment mutation, or external state change is required by this slice.
