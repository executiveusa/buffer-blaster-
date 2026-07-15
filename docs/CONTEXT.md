# CONTEXT.md — Stage 04: Implementation
# ICM Protocol: Read this before writing any code in this stage

---

## YOUR ROLE IN THIS STAGE

You are the implementation agent. You have:
- Read CLAUDE.md ✓
- Read 00_context/PROJECT.md ✓
- Read 02_specs/TDD_SPEC.md ✓
- Read 03_tests/ (failing tests exist) ✓

Now you write code that makes the failing tests pass.
One spec at a time. One module at a time. In order.

---

## INPUTS (what you read from previous stages)

```
02_specs/TDD_SPEC.md     → feature specs and test locations
03_tests/**              → failing test files
00_context/SECRETS.md    → env var names (never hardcode values)
skills/**/*.md           → skill SKILL.md files for Hermes integration
```

---

## OUTPUTS (what you produce in this stage)

```
04_implementation/
  ├── rust_core/src/     → Rust modules (encryption, auth, rate_limit, job_queue)
  ├── api/               → FastAPI backend
  │   ├── main.py
  │   ├── routers/
  │   ├── services/
  │   ├── models/
  │   └── middleware/
  ├── frontend/          → Next.js app
  │   ├── app/           → App Router pages
  │   ├── components/    → shadcn/ui + TailAdmin customized
  │   └── lib/           → API clients, utilities
  └── agents/            → Hermes agent files
      ├── SOUL.md
      ├── hermes_config.yaml
      └── sandcastle/    → per-client workflow scripts
```

---

## IMPLEMENTATION RULES

1. **Test file exists → write implementation → test passes → commit → bead**
2. **No feature without a test.** If you want to add something not in the spec, add a test first.
3. **ICM folder contract:** implementation files go in `04_implementation/`. Never in `02_specs/`.
4. **Model-agnostic:** Every AI call goes through `services/llm_adapter.py`. Never call Anthropic directly.
5. **No hardcoded secrets.** `os.getenv("KEY_NAME")` everywhere.
6. **Rust for the 4 modules:** auth, encryption, rate_limit, job_queue. Python does not handle these.
7. **Stop-slop on ALL generated text.** Every caption, blog draft, email — pipe through slop filter.
8. **Per-client schema:** Every DB query specifies `schema_{client_slug}.table_name`. Never `public.table_name` for client data.

---

## IMPLEMENTATION CHECKLIST (in order)

### Phase 1 — Foundation
- [ ] `rust_core/src/lib.rs` — encryption module (test: 03_tests/rust/test_encryption.rs)
- [ ] `rust_core/src/lib.rs` — auth module (test: 03_tests/rust/test_auth_middleware.rs)
- [ ] `rust_core/src/lib.rs` — rate_limiter (test: 03_tests/rust/test_rate_limiter.rs)
- [ ] `rust_core/src/lib.rs` — job_queue (test: 03_tests/rust/test_job_queue.rs)
- [ ] `api/routers/auth.py` — POST /api/auth/verify (test: 03_tests/auth/test_demo_auth.py)
- [ ] `api/db/client_isolation.py` — create_client_schema() (test: 03_tests/clients/test_client_isolation.py)

### Phase 2 — Platform Core
- [ ] Hermes config + skills copy (test: 03_tests/agents/test_hermes_install.sh)
- [ ] `api/services/llm_adapter.py` — model-agnostic adapter (test: 03_tests/agents/test_llm_adapter.py)
- [ ] `api/routers/pipeline.py` — run + status + cancel (test: 03_tests/pipeline/test_e2e_pipeline.py)
- [ ] `frontend/app/admin/` — dashboard + settings + clients (test: 03_tests/dashboard/)
- [ ] `api/routers/clients.py` — CRUD + CSV + Airtable sync

### Phase 3 — Content Engine
- [ ] `api/services/autoresearch.py` — Karpathy loop (test: 03_tests/autoresearch/test_ab_loop.py)
- [ ] Accessibility pass on all pages (test: 03_tests/accessibility/test_wcag.ts)

### Phase 4 — Voice
- [ ] `api/services/telegram_service.py` — bot + commands (test: 03_tests/telegram/)
- [ ] `api/routers/voice.py` — VisionClaw webhook (test: 03_tests/voice/)

### Phase 5 — Public
- [ ] `frontend/app/(public)/` — landing page + blog (test: 03_tests/landing/ + 03_tests/blog/)

### Phase 6 — Deploy
- [ ] CI/CD config + Vercel deploy (test: 03_tests/deploy/)

---

## WHEN TO STOP AND ASK STAVARAI

- Any time you need a real env var value
- If a Rust crate doesn't compile and you need to choose an alternative
- If TailAdmin component doesn't exist and you need to design from scratch
- If VisionClaw config requires hardware-specific settings
- Before making any schema change that would lose data

---

## WHAT YOU HAND OFF TO STAGE 05 (Deploy)

```
04_implementation/
  Compiled Rust library: stavarai_core.so
  FastAPI app: passes all 03_tests/
  Next.js build: 0 errors
  Hermes: configured and status OK
  All 03_tests/**/*.{py,ts,rs,sh} → passing
```

Then and only then: proceed to `05_deploy/CONTEXT.md`.
