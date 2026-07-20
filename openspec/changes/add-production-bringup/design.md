# Design: add-production-bringup

## Architecture decisions (locked, do not relitigate)

1. **Two-mode toggle.** `NEXT_PUBLIC_DEMO_MODE` flips frontend between seeded
   data and live API. Same codebase, one env var.
2. **Rust-optional.** Rust is the production hot path; pure-Python is the
   universal fallback. The loader (`api/services/native.py`) picks whichever
   is present and `/api/health` reports honestly.
3. **Per-client PostgREST schema scoping.** `api/db/repositories.py` creates
   a separate Supabase client per client schema via `ClientOptions(schema=…)`.
   This is the driver-level isolation layer; SQL-level isolation
   (`002_client_isolation.sql`) is defence-in-depth.
4. **LLM-agnostic.** `api/services/llm_adapter.py` routes by env var. No
   hardcoded model names. Provider + model both configurable.
5. **Squash-merge only.** One phase = one OpenSpec change = one PR.

## Phase dependency graph

```
A.1 push CI workflows
  └─ A.2 cargo test on VPS
       └─ A.3 drop prebuilt lib  →  /api/health core=rust

B.1 supabase db push  ──┐
B.2 RLS isolation test  │  (parallel; both gate C)
                        ├──► C.1 Hermes install
                        │     C.2 E2E pipeline spec
                        │     C.3 autoresearch loop
                        │
                        ├──► D.1 Telegram
                        │     D.2 VisionClaw
                        │
                        └──► E.1 Vercel deploy
                              E.2 a11y gate
```

## Why this order

- **A before everything.** Without CI green and Rust proven on the VPS, every
  later phase risks shipping unverifiable code.
- **B gates C.** The pipeline can't run live without a live database, and the
  RLS test must exist before any client data lands.
- **C and D parallel.** Voice control doesn't depend on the pipeline running,
  but both depend on B.
- **E last.** Public deploy is the irreversible-ish step; do it once everything
  behind it is proven.

## Test strategy (TDD, every phase)

| Phase | New test file | Asserts |
|---|---|---|
| A.2 | (Rust crate tests, already exist) | Encryption/auth/rate_limit/job_queue parity |
| B.1 | `tests/clients/test_supabase_live.py` (gated by `SUPABASE_URL` env) | Migrations apply; `create_client_schema()` works |
| B.2 | `tests/clients/test_rls_isolation.py` | anon key reads return empty on `schema_*` |
| C.1 | `tests/agents/test_hermes_install.sh` | `hermes status` reports 7 skills + Higgsfield MCP |
| C.2 | `tests/pipeline/test_e2e_pipeline.py` | queue → status → approval_queue state machine; no auto-publish |
| C.3 | `tests/autoresearch/test_ab_loop.py` | ratchet keeps improvements, reverts regressions |
| D.1 | `tests/telegram/test_bot_commands.py` | `is_stavarai()` silences non-matching IDs |
| D.2 | `tests/voice/test_visionclaw_integration.py` | transcript → intent/entity → execution |
| E.1 | (curl smoke in CI) | Deployed URLs return 200 + expected fragments |
| E.2 | axe-core in CI | Zero critical violations on public routes |

## Rollback strategy

Every phase writes `ops/rollback/<phase-id>.json` BEFORE merge:

- **Phase A** — baseline SHA + `git revert <merge-sha>` (Rust core is additive).
- **Phase B** — schema version + the reverse of each migration (drop function
  for `create_client_schema`; no client data yet to lose in dev).
- **Phase C** — feature-flag the pipeline (`HERMES_ENABLED=false`); revert
  commits; the approval queue is the hard stop on publish.
- **Phase D** — Telegram bot is purely additive; revoke bot token via
  @BotFather as the off-switch.
- **Phase E** — Vercel auto-keeps the prior prod deployment; one-click
  rollback in the Vercel dashboard.

## Tooling (mandatory per `EMERALD_TABLETS.md` Tier 5)

- **RTK** prefixes every CLI command (`rtk cargo test`, `rtk npm run build`).
  Install via `scripts/install-tools.sh`. 60–90% token compression.
- **jcodemunch** indexes the repo once per session. Agents retrieve symbols,
  not whole files. Install + MCP config via `scripts/install-tools.sh`.
- Both tools install **globally** (every project inherits them) — see
  `scripts/install-tools.sh`.
