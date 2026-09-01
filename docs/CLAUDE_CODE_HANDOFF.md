# CLAUDE_CODE_HANDOFF.md — Archived

This file formerly instructed an agent to rebuild an older Stavarai/Postatees
version of the application from scratch. It is no longer an executable handoff.
Following it would overwrite current Buffer Blaster architecture, recreate
obsolete auth/configuration, and duplicate already-shipped services.

## Current agent entrypoint

1. Read `EMERALD_TABLETS.md`.
2. Read `AGENTS.md`.
3. Read `icm/CONTEXT.md` and only the relevant current stage.
4. Inspect existing implementation before changing it.
5. Use the accepted OpenSpec for the specific change.
6. Add tests first, make the smallest repair, create rollback evidence, and open
   one PR.
7. Let CI plus OpenCodeReview independently review the PR before release.

## Current product/runtime truth

- Canonical product name: **Buffer Blaster**.
- Frontend: existing Next.js application under `frontend/`.
- Backend: existing FastAPI application under `api/`.
- Production ledger: canonical `buffer_blaster` Supabase schema.
- Rust core is optional acceleration; Python fallback remains supported.
- Secrets are runtime-only; there is no committed/default production password.
- Provider/model IDs remain environment-driven.
- Publishing and paid-media mutation remain human approval-gated.
- Production backend deployment uses `scripts/selfhost/install.sh`.
- Production Vercel setup uses `scripts/selfhost/configure-vercel.sh`.

Do not scaffold a replacement application, recreate old schemas, or copy the
historical commands from prior versions of this document.
