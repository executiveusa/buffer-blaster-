# Design — Agentic Social Studio V1

## Product boundary

The proprietary application owns brand memory, campaigns, UGC generation, scoring, approvals, analytics interpretation, agent orchestration, and the customer experience. TryPost is a replaceable publishing adapter accessed over REST. Fal is a replaceable media-generation adapter. The Social Drop contract is the boundary between content creation and publishing.

## Agent-first loop

`objective -> campaign plan -> creative brief -> UGC prompt -> render job -> score -> approval -> social drop -> TryPost -> receipt -> analytics`

Every destructive public action remains behind explicit approval.

## UI bar

Use the owner-supplied Adpanel references as the visual bar: quiet off-white surfaces, large editorial type, high whitespace, black primary actions, soft rounded cards, a two-rail application shell, compact blue/ink state accents, and a node/canvas metaphor for workflows. Borrow the proven information architecture, not the brand, logo, copy, or exact layout.

The product improvement over the reference is the persistent agent command surface: every major page can be operated manually or by a natural-language/voice command, and actions resolve to visible plans, approvals, receipts, and rollback state.

## V1 pages

Public: `/`, `/pricing`.

Product: `/studio`, `/studio/create`, `/studio/library`, `/studio/moodboards`, `/studio/canvas`, `/studio/calendar`, `/studio/campaigns`, `/studio/analytics`, `/studio/settings`.

Legacy routes stay available during V1 to avoid breaking existing demos.

## Pricing

- Creator — $39/mo: 1 brand, 5 social accounts, 3 UGC credits, scheduling, manual campaign builder.
- Growth — $119/mo: 4 brands, 20 social accounts, 12 UGC credits, agent campaign planning, analytics, approvals.
- Agency — $299/mo: 12 brands, 60 social accounts, 40 UGC credits, API/MCP/CLI, white-label exports, priority renders.

A UGC credit is defined as up to 10 seconds of standard video generation. Provider cost remains metered internally so plan economics can be tuned without changing the customer contract.

## Media prompts

The prompt compiler follows the uploaded universal video guide order: scene, camera, subject, environment, lighting/style, motion, then optional dialogue. It deliberately limits conflicting style stacking and keeps continuous motion as the default. The existing UGC skill remains the niche playbook layer.

## Interfaces

REST: `/api/studio/*`.
MCP: `/api/mcp` JSON-RPC with explicit tools.
CLI: `python -m cli.blaster ...`.
Plugin skill: `plugins/social-studio/SKILL.md`.
Voice: browser speech capture + `/api/voice/command`; deterministic intent routing with LLM enrichment only when configured.

## Safety and rollback

No database migration in this V1. Existing Supabase isolation remains untouched. Provider tokens are environment-only. TryPost scheduling requires `approved=true`. The previous frontend remains recoverable by reverting the single squash merge and redeploying the prior Vercel deployment.
