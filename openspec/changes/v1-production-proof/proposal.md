# V1 Production Proof

Status: accepted
Owner acceptance: 2026-08-28 — owner instructed the agent to proceed with the production-readiness work and merge when verified.

## Problem

The merged agentic Social Studio V1 is deployed, but the current `main` CI is not clean. The API root contract test is stale after the accepted MCP route was added, and the frontend dependency audit reports high-severity advisories. Production integrations also need a verified, non-secret configuration path before the first real publish proof.

## Outcome

Restore a green required verification path without weakening security gates, preserve the hard human approval gate for public publishing, verify the production deployment, and leave the system ready for a real draft-to-publish proof once runtime credentials and exact publish approval are available.

## Scope

- update the stale API discovery contract for the accepted `/api/mcp` route
- remove or upgrade vulnerable frontend dependency paths rather than suppressing audit failures
- preserve existing public routes and Social Studio behavior
- verify GitHub CI and the production Vercel deployment
- document rollback evidence for this slice
- keep Fal, TryPost, OpenAI, Supabase, and model/provider credentials environment-driven

## Non-goals

- no destructive database migration
- no bypass of the human approval gate
- no secret values in GitHub, logs, docs, or chat
- no new scheduler or duplicate publishing kernel
- no public post is sent as part of this change without explicit approval of the exact content
