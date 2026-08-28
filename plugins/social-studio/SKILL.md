---
name: social-studio
version: 1.0.0
description: Operate the Agentic Social Studio to plan campaigns, create UGC prompts, inspect connected social accounts, and schedule approved Social Drops.
---

# Social Studio Plugin

Use this skill when an agent needs to turn a business objective into social content, create a UGC video brief, inspect publishing readiness, or schedule content.

## Walk Test

A cold agent reads this file, then the target campaign brief. It must be able to answer: what outcome is requested, what it may create, what requires human approval, which API route or MCP tool to call, and where the returned receipt belongs.

## Interfaces

- REST base: `$BLASTER_API_URL`
- Auth: `Authorization: Bearer $BLASTER_API_KEY`
- MCP: `$BLASTER_API_URL/api/mcp`
- CLI: `python -m cli.blaster`

## Core tools

1. `studio_status` — check media/publisher readiness and the approval gate.
2. `create_campaign_plan` — turn a bounded objective into a content plan.
3. `create_ugc_prompt` — compile a provider-neutral production prompt from a UGC brief.
4. `list_social_accounts` — resolve connected TryPost social-account IDs before scheduling.
5. `schedule_social_drop` — schedule only an explicitly approved Social Drop.

## Hard rules

- Never publish or schedule unless the supplied approval is explicit and `approved=true`.
- Never invent a social-account ID. Resolve it from `list_social_accounts`.
- Never expose provider keys or internal codenames in public content.
- Treat render submission as asynchronous. Store `request_id`, `status_url`, and `response_url` as evidence.
- Keep creation provider-neutral. Campaigns and Social Drops must not depend on a specific video model or scheduler.

## UGC prompt order

Scene → camera → subject → environment → lighting/style → motion → optional dialogue. Prefer one continuous shot unless the creative brief explicitly calls for edits. Keep product identity and packaging legible.
