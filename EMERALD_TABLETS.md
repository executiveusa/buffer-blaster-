# EMERALD_TABLETS.md — The Non-Negotiables

> Highest layer of governance. Overrides everything else in this repo,
> including `AGENTS.md`, accepted specs, and agent preference. Mirrors the
> GRINIONS™ v1 prime directive: **Verify It Before Everything (V.I.B.E.)**.

## Tier 1 — Identity (never change without owner sign-off)

1. **The platform is invisible to the company.** Internal names — "Stavarai",
   "Hermes", "Buffer Blaster", "Higgsfield" — appear ONLY in `/admin/*`,
   `api/`, `rust_core/`, `docs/`, `.beads/`, and `openspec/`. Never in
   `frontend/src/app/page.tsx`, `frontend/src/app/blog/**`, or `content/blog/**`.
2. **One operator.** No multi-tenant auth, no OAuth. `BLASTER2026` is the only
   backend access. Change it post-demo via `.env`, never in code.
3. **Built to sell.** Every architectural decision must make the platform more
   acquirable: teachable, unique, repeatable. See `docs/BUILT_TO_SELL.md`.

## Tier 2 — Data & Security

4. **No client data mixing.** Each client gets an isolated `schema_{slug}`
   Postgres schema, enforced by `supabase/migrations/002_client_isolation.sql`
   and verified by `tests/clients/test_client_isolation.py`. Any change to
   isolation must update both.
5. **Production writes require the service key.** The anon key is read-only on
   published blog posts and nothing else. RLS is on every public table.
6. **Never log secrets.** `BLASTER2026` and API keys may not appear in stdout,
   stderr, commits, error messages, or analytics. The auth test enforces this.
7. **No auto-publish.** The publisher only fires on explicit human approval.
   The approval queue is the gate; there is no override.

## Tier 3 — Engineering discipline

8. **Tests before code.** Every new feature ships with a failing test that
   passes after implementation. No disabling tests to pass — fix the test or
   fix the code.
9. **LLM-agnostic.** No hardcoded model names. All model calls go through
   `api/services/llm_adapter.py`. Provider + model are env-driven.
10. **Rust is never a hard dependency.** The Rust crate and the pure-Python
    fallback in `api/services/native.py` share one contract. The loader picks
    Rust if a prebuilt lib is present, else Python. `/api/health` honestly
    reports which backend is live.
11. **Scoring rubric is fixed:** Hook 25 / Platform 20 / Niche 20 / Trend 15 /
    Visual 10 / Audience 10 = 100. Per-client weights tunable by the
    autoresearch loop only.

## Tier 4 — Release discipline (GRINIONS™-aligned)

12. **Squash-merge only.** Never force-push `main`. One phase = one OpenSpec
    change = one PR.
13. **One bead per destructive op.** `.beads/{timestamp}_{action}.bead` is
    written BEFORE any schema change, deploy, weight commit, or data migration.
14. **Rollback is proven before merge.** Every phase PR includes
    `ops/rollback/<phase-id>.json` with baseline SHA, deployment ID, and
    tested rollback commands. No proven rollback → no merge.
15. **Stop-slop on all generated text.** No "AI-powered", "revolutionize",
    "unlock", "elevate", "leverage". See `skills/stop-slop/SKILL.md`.

## Tier 5 — Operating tools (mandatory for autonomous agents)

16. **jcodemunch is the default retrieval layer.** Index once per session,
    retrieve symbols — don't dump whole files into context.
17. **RTK prefixes every CLI command** when installed (`rtk cargo test`,
    `rtk npm run build`). 60–90% token compression. See
    `scripts/install-tools.sh`.

## §6 — STOP conditions (stop for human decision, not for routine friction)

Stop only when:
- business intent is ambiguous, or project truth conflicts
- a destructive migration is required, or rollback can't be proven
- secret exposure is detected
- production payment behavior changes
- auth/permission safety can't be proven, or blast radius > 3 services
- CI/review repair budget is exhausted (5 local / 2 remote / 3 review rounds)
- a merge requires bypassing branch protection, or proceeding weakens security
- tests can't distinguish safe from unsafe behavior
- legal/compliance decision is required

Do NOT stop for: lint errors, test failures, merge conflicts, nits, routine
review feedback. Repair them within budget and continue.
