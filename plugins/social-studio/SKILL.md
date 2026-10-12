---
name: social-studio
version: 1.2.0
description: Operate Buffer Blaster as an internal creative-production tool from Claude Code, Codex, or another authorized agent. Plan, inspect receipts, and request human-approved generation.
---

# Buffer Blaster — internal agent skill

Use Buffer Blaster to turn a real client/product brief into creative plans, governed
UGC production, final assets, and verifiable cost/QA receipts. This is an
**in-house tool**, not a low-ticket subscription product. Do not invent client
outcomes, provider status, or revenue.

## Connection

- MCP transport for Claude Code/Codex: `python -m cli.mcp_stdio`
- Runtime environment: `BLASTER_API_URL` and `BLASTER_API_KEY`
- Canonical backend MCP: `$BLASTER_API_URL/api/mcp`
- REST: `$BLASTER_API_URL/api/studio`
- CLI: `python -m cli.blaster`
- Installation and walk test: `docs/AGENT_MCP_SETUP.md`

Use the MCP server's live `tools/list` as the authority for tool names and
schemas. All interfaces share the same backend and approval gates.

## No-spend default workflow

1. `studio_status` — inspect ledger, provider, storage, and approval readiness.
2. `list_provider_capabilities` and `plan_provider_route` — inspect available
   routes and estimated cost; do not assume a named provider is active.
3. `create_campaign_plan`, `create_ugc_prompt`, `create_ugc_plan`, or
   `create_ugc_ad_factory_plan` — prepare a reviewable plan from product truth.
4. `get_ugc_plan`, `list_creative_jobs`, and `get_creative_job` — inspect
   canonical receipts and avoid invented completion claims.
5. Present creative plan, route, expected cost, and exact deliverables to the
   human operator for review. **Stop before any consequential action.**

## Human-approved execution only

- `get_usage_wallet` — inspect a server-owned active wallet, never a guessed ID.
- `execute_ugc_ad_factory` — use only after explicit human approval of the
  exact job, with `approved=true`, a server-issued wallet ID, and an
  idempotency key. Server-side budget reservation is mandatory.
- `list_social_accounts` and `schedule_social_drop` — optional downstream
  publishing, only with actual account IDs and explicit human approval.
- Never turn a prior approval into blanket permission for future paid jobs.

## Non-negotiable rules

- No raw or single-clip paid generation bypass. Paid production stays behind
  the governed factory and server-owned wallet.
- Never put API keys, service-role credentials, provider secrets, or client
  data in prompts, skill files, commits, screenshots, or ordinary logs.
- Never invent a social account, wallet, provider request, asset URL, cost,
  performance result, or completion state.
- A queued job is not a delivered ad. Confirm a durable completed job,
  final asset, and QA/cost receipt before claiming delivery.
- Client/workspace isolation is mandatory. Use only authorized workspace
  context and credentials.
- Publishing, paid-media activation, and provider spending require explicit
  human approval; do not bypass server enforcement.
- Keep provider/model choices configurable; do not hardcode model IDs.
- A tool being listed does not mean its external integration is live.

## Production order

Product truth → angle/script → no-spend plan → provider/cost preflight →
human review → wallet and approval gate → provider generation →
continuity/QA → final asset → durable cost/approval receipt → optional
approved publishing → measured iteration.

## Verification

Use the no-spend walk test in `docs/AGENT_MCP_SETUP.md`. Never claim the
production system is finished until `GATES.production.md` is verified with
current evidence.
