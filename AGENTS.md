# AGENTS.md — Operating Contract

> Read `EMERALD_TABLETS.md` first. It overrides this file. Orchestrator: GRINIONS™ v1.

## Identity & Boundaries
- Internal platform: **Stavarai Platform** | Repository: **Buffer Blaster** | Public: **Social Studio**.
- Buffer Blaster is a standalone application. External publishers are optional downstream integrations (see `docs/APP_BOUNDARIES.md`).
- Repository: `https://github.com/executiveusa/buffer-blaster-` | Default branch: `main` (squash-merge only).

## Architecture
- `frontend/`: Next.js product + public site
- `api/`: FastAPI operational backend + services
- `plugins/social-studio/`: portable agent skill/plugin
- `cli/`: scriptable operator client | `rust_core/`: runtime primitives with Python fallback
- `supabase/`: migrations and isolation boundary | `skills/`: creative/quality skills
- `openspec/`: accepted change contracts | `ops/`: receipts and rollback evidence

## Agent Interfaces & Security
- Interfaces: REST (`/api/studio/*`), MCP (`/api/mcp`), CLI (`python -m cli.blaster`), Plugin (`plugins/social-studio/SKILL.md`), Voice (`/api/voice/command`).
- All interfaces share the human approval gate for scheduling/publishing.
- Database: retain schema-scoped access and current RLS rules.
- Secrets: runtime environment variables only; never commit secrets.

## Working Agreement
1. Verify before claiming completion.
2. Tests before implementation.
3. One accepted OpenSpec change = one PR.
4. Squash-merge only.
5. No public internal codenames.
6. No public publishing without explicit human approval.
7. No hardcoded LLM or media model IDs in runtime code.
8. Every deploy/destructive op gets bead + rollback evidence first.
9. Do not bypass CI, RLS, auth, or secret controls to ship faster.
10. Use the smallest change that produces real evidence.
11. Never merge another application's code, database, secrets, deployment, or identity into Buffer Blaster.
