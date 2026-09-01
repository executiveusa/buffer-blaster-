# CLAUDE.md — Buffer Blaster Agent Router

This file is a compatibility entrypoint for coding agents. It is intentionally
small so it cannot become a second source of truth.

## Read order

1. `EMERALD_TABLETS.md` — non-negotiable governance; overrides everything else.
2. `AGENTS.md` — repository operating contract and application boundary.
3. `icm/CONTEXT.md` — route to the smallest current campaign/experiment context.
4. The accepted OpenSpec for the change you are actually implementing.
5. Relevant tests and existing implementation before writing code.

## Current identity

- Product/repository application: **Buffer Blaster**.
- Frontend: `frontend/` (Next.js).
- Backend: `api/` (FastAPI).
- Canonical production state: `buffer_blaster` Supabase schema.
- Optional hot path: `rust_core/`; Python fallback remains valid.
- Agent interfaces: REST, MCP, CLI, plugin, voice.
- Publishing and paid-media mutation require explicit human approval.

## Current production path

- VPS/backend: `scripts/selfhost/install.sh`
- Vercel frontend: `scripts/selfhost/configure-vercel.sh`
- Verification: `scripts/selfhost/preflight.sh` + `scripts/selfhost/smoke.sh`
- Secrets: `docs/SECRETS.md`

Do not reconstruct the application from old handoffs. Do not create a parallel
Stavarai/Postatees deployment, schema, auth system, or provider path. Inspect and
repair the existing Buffer Blaster implementation in one verifiable slice.
