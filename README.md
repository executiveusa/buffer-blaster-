# Stavarai Platform

Private, enterprise-grade AI content-operations platform. Built for one operator
(Stavarai), trained on real client data, positioned for acquisition.

> **This repo is internal.** No client data, no internal architecture, no agent
> names should ever appear in public-facing surfaces (landing page, blog).

## What this is

An AI-driven content engine for a Shopify-brand social media agency serving four
niches: Food & Beverage, Beauty & Skincare, Apparel & Accessories, and Home &
Lifestyle. It researches, generates, scores, and schedules social content at a
volume no human team can match — then learns from what works.

The company never sees how it works. They see results.

## Quick start

### Demo mode (what you show people)

No backend, no secrets, no setup. Renders the full UI with seeded data.

```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

- Landing page at `/`
- Blog at `/blog`
- Admin gate at `/admin` — password: `BLASTER2026`

### Full stack (local dev)

```bash
npm install                       # workspaces (frontend)
cd api && pip install -r requirements.txt && cd ..
npm run dev:local                 # FastAPI :8000 + Next.js :3000
```

### Production (VPS)

See **`docs/HANDOFF.md`** for the complete VPS setup, or run `setup.sh` on a
Linux server. Frontend deploys to Vercel.

## Repository layout

```
frontend/        Next.js 15 + Tailwind v4 — landing, admin, blog
api/             FastAPI — auth, dashboard, clients, pipeline, settings, voice
rust_core/       AES-256 encryption, session auth, rate limiter, job queue
supabase/        Migrations — schema, client isolation, demo seed
skills/          grill-me, stop-slop, food-beverage, ugc-video, scoring
content/blog/    MDX posts (original, value-add)
agents/          Hermes SOUL.md + config
docs/            Specs, secrets contract, TDD spec, acquisition playbook
tests/           TDD — Rust + Python
.beads/          Reversible checkpoints (every destructive op logs one)
```

## Read these first

1. `docs/CLAUDE.md` — root orientation (ICM structure, 10 core laws)
2. `docs/PROJECT.md` — who this is for, what it does, acquisition framing
3. `docs/SECRETS.md` — every env var, where it lives, never hardcoded
4. `docs/TDD_SPEC.md` — every feature as a test, before code
5. `docs/HANDOFF.md` — what runs now, what needs a VPS, the 7 gaps to fill

## Core laws

1. **Tests before code.** Every feature has a failing test first.
2. **No client data mixing.** Each client gets an isolated Supabase schema.
3. **Stop-slop on all generated text.** No "AI-powered", no "revolutionize".
4. **LLM-agnostic.** No hardcoded model names. Swap providers in settings.
5. **One bead per destructive op.** `.beads/` is the audit trail.
6. **Rust for the hot path.** Auth, encryption, rate-limiting, job-queuing.
7. **`BLASTER2026` is the only backend access.** Backend greets Stavarai by name.

## Security

- All API keys encrypted at rest (AES-256-GCM via Rust core)
- Supabase RLS on every public table
- Per-client schema isolation (verified by test)
- Telegram bot ignores every user except Stavarai's ID
- `.env` is gitignored and chmod 600 on the VPS

## License

Proprietary. All rights reserved. See `docs/BUILT_TO_SELL.md`.
