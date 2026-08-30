---
name: social-studio
version: 1.1.0
description: Operate Social Studio to plan campaigns, build gated UGC ads, inspect pricing/wallet state, review receipts, and schedule explicitly approved social drops.
---

# Social Studio Plugin

Use this skill when an agent needs to turn product truth or a business objective into reviewable social creative. The same commercial and approval boundaries apply through REST, MCP, CLI, voice, and UI.

## Walk Test

A cold agent must be able to answer: what outcome is requested, what can be planned without spend, what requires explicit approval, which wallet funds paid generation, which API/MCP tool to call, and where the resulting job/QA/cost receipt is stored.

## Interfaces

- REST base: `$BLASTER_API_URL/api/studio`
- Auth: `Authorization: Bearer $BLASTER_API_KEY`
- MCP: `$BLASTER_API_URL/api/mcp`
- CLI: `python -m cli.blaster`

## Core tools

1. `studio_status` — provider/storage/ledger/pricing readiness plus approval state.
2. `get_pricing` — current sellable packages and provider-spend ceilings.
3. `create_campaign_plan` — create and persist a bounded campaign plan.
4. `create_ugc_ad_factory_plan` — product truth -> deterministic scripts, gates, continuity plan, and estimated generation reserve. This makes no paid generation call.
5. `get_usage_wallet` — inspect the server-owned wallet before paid generation.
6. `execute_ugc_ad_factory` — after explicit approval, reserve wallet allowance and run the full ad workflow through final asset + QA receipt.
7. `list_ugc_jobs` / `get_ugc_job` — inspect durable execution state and provider evidence.
8. `list_social_accounts` — resolve connected downstream account IDs.
9. `schedule_social_drop` — schedule only an explicitly approved Social Drop.

## Hard rules

- Never publish or schedule unless `approved=true` is supplied by the human/operator.
- Never call a raw or single-clip paid generation route. Paid generation goes through `execute_ugc_ad_factory` with a server-issued active wallet.
- Never trust browser/agent-supplied credit balances. Wallet balance and provider budget are server-owned and reserved atomically before media generation.
- Never invent a social account ID, wallet ID, provider request ID, asset URL, performance result, or completion state.
- A queued provider request is not a completed ad. Completion requires the durable job receipt to reach `completed` with a final asset and QA state.
- Keep model IDs provider/configuration driven. Do not hardcode a media model in campaign or plugin logic.
- Never expose provider keys, internal codenames, or private storage credentials in public content.
- Publishing is optional and downstream; the core UGC factory does not depend on any specific scheduler.

## UGC factory order

Product truth -> script gate -> cast direction -> approval -> spend reservation -> clip 1 -> trim -> seed frame -> clip 2 -> seam QA -> bounded retry when needed -> stitch -> final asset storage -> durable cost/QA/provider receipt.

## Commercial rule

One Ad Credit covers up to the configured standard provider-cost ceiling. Higher estimated-cost work consumes multiple Ad Credits. A generation request must fit both the remaining Ad Credits and the remaining provider-cost wallet before a paid provider call is allowed.
