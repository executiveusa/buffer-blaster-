# AGENTS.md — Operating Contract for the Stavarai Platform

> Read this before writing any code. It overrides preference but is itself
> overridden by `EMERALD_TABLETS.md`. Orchestrator: GRINIONS™ v1.

## What this repo is

A private, enterprise-grade AI content-operations platform for a Shopify-brand
social-media agency. One operator (Stavarai). Goal: prove value, then position
for a **$500K acquisition** (see `docs/BUILT_TO_SELL.md`).

## The one rule that overrides everything

**The company must never see how this works.** No "Hermes", "Buffer Blaster",
"Stavarai", or internal architecture on any public surface. They see results.
The operator sees the engine.

## Workspace map

```
frontend/      Next.js 16 + Tailwind v4 — landing, admin, blog
api/           FastAPI — auth, dashboard, clients, pipeline, voice, settings
rust_core/     AES-256-GCM, sessions, rate limiter, job queue (cdylib)
supabase/      migrations 001-004
skills/        grill-me, stop-slop, food-beverage, ugc-video, scoring
content/blog/  MDX posts
openspec/      accepted specs (source of truth — overrides chat history)
ops/           reports/, receipts/, rollback/ — zero-context handoff artifacts
.beads/        long-horizon work memory
.ralphy/       bounded-implementation-loop config
```

## Working agreement

1. **Verify before everything (V.I.B.E.).** No claim of "done" without a green
   test or command output pasted in the bead/PR.
2. **Spec is truth.** Once an OpenSpec change is accepted, chat history is not.
3. **Tests before code.** Failing test → implement → green → commit. Always.
4. **One bead per destructive op.** Schema change, deploy, weight commit, data
   migration — `.beads/{timestamp}_{action}.bead` first.
5. **Squash-merge only.** One phase = one OpenSpec change = one PR. Never
   force-push `main`.
6. **Use repo intelligence first.** Run `jcodemunch index` once per session and
   retrieve symbols instead of whole-file reads. Prepend `rtk` to every CLI
   command for 60–90% token compression (see `scripts/install-tools.sh`).
7. **Stop conditions** are listed in `EMERALD_TABLETS.md` §6. Don't ask
   "should I continue?" between successful approved phases.

## Commands (all should be prefixed with `rtk` when RTK is installed)

```bash
rtk cargo test --manifest-path rust_core/stavarai_core/Cargo.toml   # Rust core
rtk python -m pytest tests -q                                       # API tests
cd frontend && rtk npm run lint && rtk npm run build                # Frontend gates
cd api && python main.py                                            # Run API (:8000)
cd frontend && npm run dev                                          # Run frontend (:3000)
```

## Credentials policy

- `.env` is gitignored. Always.
- `BLASTER2026` and any API key may never appear in logs, commits, or public
  surfaces. The auth test asserts this — keep it green.
- Implementation agents do not hold the credential that can merge `main` or
  deploy production. Those are deterministic privileged jobs.

## When you're stuck

- Read `docs/HANDOFF.md` (the production roadmap, phases A–E).
- Read `EMERALD_TABLETS.md` (the non-negotiables).
- Check `.beads/` for the last reversible checkpoint.
- File an OpenSpec change rather than editing accepted specs in chat.
