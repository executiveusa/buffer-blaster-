# OpenSpec — Project Context

## Project

**Stavarai Platform** — private, enterprise-grade AI content-operations system
for a Shopify-brand social-media agency. Repository:
`https://github.com/executiveusa/buffer-blaster-.git`.

## Why it exists

Two young operators inside the company are building the engine the agency will
eventually depend on. The goal is to prove value to clients before asking for
money, then position the platform for a **$500K acquisition** (cash + stock +
12-month retention) per the Built-to-Sell playbook in `docs/BUILT_TO_SELL.md`.

## The one rule

The company must never see how this works. They see results. The operators see
the engine. Internal names — "Stavarai", "Hermes", "Buffer Blaster",
"Higgsfield" — never appear on public surfaces.

## Operating model

- **One operator** (Stavarai). `BLASTER2026` is the only backend access.
- **GRINIONS™ v1 orchestration.** Source of truth precedence:
  `EMERALD_TABLETS.md` → `AGENTS.md` → accepted OpenSpec → beads → preference.
- **Two runtime modes.** `NEXT_PUBLIC_DEMO_MODE=true` (default, no backend) vs
  `=false` + `NEXT_PUBLIC_API_URL` (production, calls FastAPI + Rust + Supabase).
- **Hot-path core.** Rust crate + pure-Python fallback share one contract
  (`api/services/native.py`). Loader picks Rust if a prebuilt lib is present.

## Current state (2026-07-20)

- Frontend, FastAPI, Rust core, Supabase migrations: **built and green**.
- `pytest tests` → 46/46 passing. `npm run build` → 22 routes, 0 errors.
- On `main` at `18e9919`. CI workflows (`build-core.yml`, `test-api.yml`) live.
- **Demo mode runs anywhere** (Windows box, no compiler, no secrets).
- **Production not yet brought up.** That is the next phase of work, governed
  by the change specs in `openspec/changes/`.

## Capabilities (durable specs live under `openspec/specs/`)

- `content-pipeline` — research → ideation → video → score → approve → publish
- `client-isolation` — per-client `schema_{slug}`, RLS, no cross-client reads
- `scoring` — 6-dimension rubric, fixed weights (Hook 25/Plat 20/Niche 20/Tr 15/Vis 10/Aud 10)
- `voice-control` — Telegram bot + Meta glasses, operator-only
- `production-readiness` — VPS bring-up, Supabase live, Vercel, autoresearch loop

## How to propose change

1. Open `openspec/changes/<change-id>/` with `proposal.md`, `design.md`,
   `tasks.md`, `specs/` deltas.
2. Get explicit owner acceptance.
3. Once accepted, chat history is no longer truth — the change spec is.
4. Implement per GRINIONS phase contract: one change = one phase = one PR.
