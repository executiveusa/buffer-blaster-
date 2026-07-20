# Tasks: add-production-bringup

> Each task is a bead. Each phase is a PR. Each PR includes the rollback
> contract. TDD: failing test FIRST, then implement, then prove green.

## Phase A — VPS bring-up

- [ ] A.1 Push `.github/workflows/{build-core,test-api}.yml` (workflow scope)
  - verify: Actions tab shows both green on win/linux/mac matrix
  - rollback: `git revert <sha>` (workflows are additive)
- [ ] A.2 On VPS: `cd rust_core/stavarai_core && cargo test` → all green
  - if any test fails: STOP. Rust/Python contract has diverged.
- [ ] A.3 Download linux artifact → `rust_core/native/libstavarai_core.so`
  - verify: `GET /api/health` returns `"core": "rust"`
  - rollback: delete the file → falls back to Python

## Phase B — Live Supabase

- [ ] B.1 Write `tests/clients/test_supabase_live.py` (gated by `SUPABASE_URL`)
- [ ] B.1 Run `supabase link --project-ref $REF && supabase db push` → 0 errors
- [ ] B.1 Verify `SELECT create_client_schema('cella-coffee')` → `schema_cella_coffee`
- [ ] B.2 Write `tests/clients/test_rls_isolation.py` (anon key reads return empty)
- [ ] B.2 Verify RLS on every `schema_*` table

## Phase C — Live pipeline

- [ ] C.1 Clone Hermes → `/opt/hermes`; copy `skills/*` → `~/.hermes/skills/`
- [ ] C.1 Write `tests/agents/test_hermes_install.sh`; verify `hermes status`
- [ ] C.2 Write `tests/pipeline/test_e2e_pipeline.py` (mock Hermes, assert
       queue → status → approval_queue state machine, NO auto-publish)
- [ ] C.2 Implement pipeline runner wiring Rust queue → Hermes orchestrator
- [ ] C.3 Write `tests/autoresearch/test_ab_loop.py` (ratchet semantics)
- [ ] C.3 Implement nightly autoresearch loop (Karpathy pattern)

## Phase D — Voice control

- [ ] D.1 Register Telegram bot via @BotFather; set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_USER_ID`
- [ ] D.1 Write `tests/telegram/test_bot_commands.py`; verify non-operator silence
- [ ] D.1 Wire Whisper transcription → intent → Hermes command
- [ ] D.2 Write `tests/voice/test_visionclaw_integration.py`
- [ ] D.2 Configure Meta glasses → VPS webhook

## Phase E — Public surfaces

- [ ] E.1 Set `VERCEL_PROJECT_ID` + `VERCEL_TOKEN`; `vercel deploy --prod`
- [ ] E.1 CI smoke: curl deployed URLs, assert 200 + fragments
- [ ] E.1 Assert `NEXT_PUBLIC_DEMO_MODE=false` in Vercel prod env
- [ ] E.2 Add axe-core CI job; assert zero critical violations
- [ ] E.2 Grep gate: `grep -riE 'stavarai|hermes|buffer.?blaster|higgsfield' frontend/src content/blog` → only admin/docs matches

## Cross-cutting

- [ ] Every phase PR includes `ops/rollback/<phase-id>.json` with `tested: true`
- [ ] Every phase writes a `.beads/<timestamp>_<action>.bead` before destructive ops
- [ ] Final report in `ops/reports/add-production-bringup.json` (zero-context handoff)
