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
- Studio at `/studio`
- Admin at `/admin`

### Full stack (local dev)

```bash
npm install                       # workspaces (frontend)
cd api && pip install -r requirements.txt && cd ..
npm run dev:local                 # FastAPI :8000 + Next.js :3000
```

### Production backend — one click

The canonical production shape is **Vercel frontend + self-hosted FastAPI backend**.
Point an API hostname at a clean Ubuntu/Debian VPS, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/executiveusa/buffer-blaster-/main/scripts/selfhost/install.sh \
  | sudo bash -s -- --domain api.example.com
```

The installer brings up FastAPI behind Caddy/HTTPS, generates app-owned secrets
locally, and leaves third-party credentials blank for secure operator entry.

Then follow **`docs/GEMINI_BETA_HANDOFF.md`** to connect Supabase, OpenAI, Fal,
TryPost and switch the canonical Vercel frontend into live mode. Run
`bash scripts/selfhost/preflight.sh` and `bash scripts/selfhost/smoke.sh` before
beta users enter.

## Repository layout

```
frontend/        Next.js + Tailwind — landing, studio, admin, blog
api/             FastAPI — auth, dashboard, pipeline, Studio, voice, MCP
rust_core/       optional Rust hot path; Python fallback remains supported
supabase/        migrations and Buffer Blaster production state
skills/          content, UGC, scoring and agent skills
content/blog/    MDX posts
agents/          Hermes/orchestration configuration
docs/            specs, secrets contract and production handoffs
scripts/selfhost one-click VPS, preflight, smoke and Vercel live-mode helpers
tests/           Python/Rust/frontend/packaging verification
.beads/          reversible checkpoints
```

## Read these first

1. `EMERALD_TABLETS.md` — non-negotiables
2. `AGENTS.md` — operating contract
3. `docs/SECRETS.md` — secrets contract
4. `docs/HANDOFF.md` — production roadmap
5. `docs/GEMINI_BETA_HANDOFF.md` — exact beta bring-up and proof sequence

## Core laws

1. **Tests before code.** Every feature has a failing test first.
2. **No client data mixing.** Client/workspace isolation is enforced in the data layer.
3. **Stop-slop on generated text.** No generic filler copy.
4. **LLM-agnostic.** Model/provider IDs stay environment-driven.
5. **One bead per destructive op.** `.beads/` is the audit trail.
6. **Rust may accelerate the hot path, but must never be a hard runtime dependency.**
7. **Production operator access must be explicitly configured.** The API has no committed fallback password.
8. **No public publishing without explicit human approval.**

## Security

- API keys are never committed; production secrets live in private runtime environment files/stores.
- The self-host container runs as a non-root user behind Caddy TLS.
- Supabase RLS/workspace controls protect production state.
- `.env.production` is gitignored and should remain `chmod 600` on the VPS.
- Provider/API secrets must never use a `NEXT_PUBLIC_*` name.

## License

Proprietary. All rights reserved. See `docs/BUILT_TO_SELL.md`.
