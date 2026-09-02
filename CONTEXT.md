# CONTEXT — Buffer Blaster

## Job
Buffer Blaster is private creative infrastructure for client work. It turns product and customer context into creative concepts and UGC-style assets, keeps approvals and cost controls with the work, and records evidence for the next iteration.

## Commercial model
The software is infrastructure, not the primary offer. It is used in managed client engagements or deployed as a dedicated private instance. Do not reintroduce low-ticket public subscription positioning without an explicit product decision.

## System map
- `frontend/` — public site, Studio, admin/operator UI.
- `api/` — FastAPI services, auth boundary, providers, money loop, MCP, voice.
- `cli/` — remote/operator command surface.
- `supabase/` — canonical schema, RLS, migrations.
- `skills/` — stable creative and quality procedures.
- `docs/` — architecture, boundaries, production, positioning, handoffs.
- `ops/` — receipts, gauntlet evidence, rollback artifacts.
- `tests/` — executable truth for the system.

## Current production truth
- Canonical branch: `main`.
- Production backend: self-hosted VPS + self-hosted Supabase.
- Current public frontend deployment is separate from the backend.
- Paid-network account activation is optional and credential-bound; never imply Meta/TikTok/Shopify account verification when credentials are absent.

## Human checks
Before merge or deploy, verify tests, security boundaries, approval gates, public copy truthfulness, mobile behavior, and rollback evidence. A deploy is not proof by itself.

## Walk test
A cold agent should be able to answer where to work after reading `AGENTS.md` + this file + one area `CONTEXT.md`. If more is required, fix routing rather than stuffing more content here.
