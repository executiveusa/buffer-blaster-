# HANDOFF — Stavarai Platform → GPT-5.6 Sol

> Format adapted from `willseltzer/claude-handoff`.
> Audience: the next agent (you), picking up a working codebase and taking it to production.
> Read this entire file before writing a single line of code.

---

## 0. Who you are and what you're holding

You are taking over the **Stavarai Platform** — a private, enterprise-grade AI
content-operations system for a Shopify-brand social media agency. Two young
operators (Stavarai + partner) inside the company built it to (a) add value to
clients before asking for money and (b) position the platform for a **$500K
acquisition** (cash + stock + 12-month retention) per the Built-to-Sell
playbook in `docs/BUILT_TO_SELL.md`.

**The single rule that overrides everything:** the company must never see how
this works. They see results. The operators see the engine. No "Buffer Blaster",
no "Hermes", no internal architecture ever appears on a public surface.

**You are not building a demo. You are hardening a working codebase for
production on a Linux VPS + Vercel.** Demo mode already works. Your job is the
production layer.

---

## 1. State — what exists RIGHT NOW (verify before trusting)

Repo: `https://github.com/executiveusa/buffer-blaster-.git`, branch `main`.

```
buffer blaster/
├─ frontend/        Next.js 16 + React 19 + Tailwind v4 — LANDING + ADMIN + BLOG
├─ api/             FastAPI — auth, dashboard, clients, pipeline, content, blog, voice, settings
├─ rust_core/       Cargo crate: AES-256-GCM, sessions, rate limiter, job queue
├─ supabase/        migrations 001-004 (schema, client isolation, seed, blog_posts)
├─ skills/          grill-me, stop-slop, food-beverage, ugc-video, scoring  (5 SKILL.md files)
├─ content/blog/    7 original MDX posts, backdated Jun 15 – Jul 6 2026
├─ scripts/         client_pipeline.ts (Sandcastle), sync_airtable.py (working)
├─ tests/           pytest (37/37 green) + Rust integration tests
├─ .github/workflows/  build-core.yml + test-api.yml (PARKED — see §7)
├─ docs/            ALL specs: CLAUDE, PROJECT, SECRETS, TDD_SPEC, BUILT_TO_SELL, etc.
└─ .beads/          reversible checkpoints (Steve Yegge format)
```

**Proven green on the build machine (Windows, no compiler):**
- `cd frontend && npm run build` → 22 routes, 0 errors, 7 blog posts prerendered
- `python -m pytest tests` → 37/37 passing
- Rust core: source + tests written; **cannot compile on the dev machine**
  (no MSVC linker / no gcc). Pure-Python fallback in `api/services/native.py`
  implements the identical contract and is what runs today. CI builds the Rust
  lib cross-platform once the workflow file is pushed (§7).

**Two operating modes (already wired, do not change the toggle contract):**
- `NEXT_PUBLIC_DEMO_MODE=true` (default) → frontend renders with seeded data, no backend.
- `NEXT_PUBLIC_DEMO_MODE=false` + `NEXT_PUBLIC_API_URL` → frontend calls FastAPI.

---

## 2. Decisions already locked (do not relitigate)

1. **Monorepo, one operator, password-gated.** No OAuth, no multi-tenant auth.
   `BLASTER2026` is the only backend access. Change it post-demo.
2. **Per-client schema isolation.** `schema_{sanitized_slug}`, verified by test.
   Never `public.` for client data. Function: `supabase/migrations/002_client_isolation.sql`.
3. **Rust for the hot path, Python everywhere else.** The Rust crate and the
   Python fallback share one contract (`api/services/native.py`). The loader
   picks Rust if a prebuilt lib is present, else Python. **Never** make Rust a
   hard dependency.
4. **LLM-agnostic.** No hardcoded model names. `services/llm_adapter.py` routes
   by `ACTIVE_LLM_PROVIDER`. Swap providers in settings, never in code.
5. **Stop-slop on all generated text.** No "AI-powered", "revolutionize",
   "unlock", "elevate". See `skills/stop-slop/SKILL.md`.
6. **Scoring rubric is fixed:** Hook 25 / Platform 20 / Niche 20 / Trend 15 /
   Visual 10 / Audience 10 = 100. Per-client weights tunable by the autoresearch loop.
7. **Built-to-Sell framing.** Every architectural choice must make the platform
   more acquirable (teachable, unique, repeatable). See `docs/BUILT_TO_SELL.md`.

---

## 3. Next actions — in strict order (TDD, every step)

Each item is a **Given/When/Then** spec. Write the failing test FIRST, then
implement, then prove green, then commit with a bead. Do not skip ahead.

### PHASE A — VPS bring-up (do this first, unlocks everything)

**A.1 Push the parked CI workflows.** On a machine with `gh auth refresh -s workflow`:
```bash
cd buffer-blaster-
git add .github/workflows && git commit -m "ci: build core + test api" && git push
```
Verify: GitHub Actions tab shows `build-core` (win/linux/mac matrix) + `test-api` green.

**A.2 Prove the Rust core.** On the VPS (Linux, gcc present):
```bash
cd rust_core/stavarai_core && cargo test
```
Expected: all encryption/auth/rate_limiter/job_queue tests pass. If any fail,
**stop** — the Python fallback contract and the Rust contract have diverged.
Fix the divergence, do not paper over it.

**A.3 Drop the prebuilt lib into place.** Download the linux artifact from the
`build-core` run → `rust_core/native/libstavarai_core.so`. Restart FastAPI.
Verify `GET /api/health` returns `"core": "rust"`.

### PHASE B — Production data layer

**B.1 SUPABASE_SPEC**
```
GIVEN: Stavarai's SUPABASE_PROJECT_REF + SUPABASE_SERVICE_KEY are in .env
WHEN:  supabase link --project-ref $REF && supabase db push
THEN:  migrations 001-004 apply with zero errors
AND:   SELECT create_client_schema('cella-coffee') returns 'schema_cella_coffee'
AND:   a row in public.beads records the schema creation
TEST:  extend tests/clients/test_client_isolation.py with a live-Supabase path
       (gated by SUPABASE_URL env) that asserts cross-schema reads are empty.
```

**B.2 SUPABASE_RLS_SPEC** (security — non-negotiable)
```
GIVEN: two clients exist (schema_a, schema_b) with content_units rows
WHEN:  a query scoped to schema_a runs
THEN:  zero rows from schema_b are returned
AND:   anon key reads return empty on all schema_* tables
AND:   service_role is the only role that can write
TEST:  tests/clients/test_rls_isolation.py (NEW) — uses the anon key to attempt
       a cross-schema SELECT and asserts it returns nothing.
```

### PHASE C — The live pipeline (this is the moat)

**C.1 HERMES_SPEC**
```
GIVEN: Hermes (NousResearch/hermes-agent) cloned to /opt/hermes with skills/ copied
WHEN:  hermes status
THEN:  reports "7 skills loaded | MCP: higgsfield connected"
TEST:  tests/agents/test_hermes_install.sh (NEW) — asserts the status string.
```

**C.2 PIPELINE_E2E_SPEC**
```
GIVEN: a client with a completed interview (brief_yaml in schema_{slug}.interviews)
WHEN:  POST /api/admin/pipeline/{slug}/run
THEN:  a Rust job-queue job is enqueued (<1ms)
AND:   a Hermes child orchestrator picks it up
AND:   status updates stream via Supabase realtime to the dashboard
AND:   on completion, schema_{slug}.approval_queues is populated
AND:   on failure, absurd retries 3× then writes a bead + Telegrams Stavarai
TIMEOUT: 4 hours max (video generation)
TEST:  tests/pipeline/test_e2e_pipeline.py (NEW) — mocks Hermes, asserts the
       queue→status→approval-queue state machine end to end.
```

**C.3 AUTORESEARCH_SPEC** (Karpathy loop, adapted)
```
GIVEN: a client with 10+ approved posts and engagement data
WHEN:  cron runs the autoresearch loop nightly at 02:00
THEN:  it reads research/{slug}/research.md (current weights + hypothesis)
AND:   proposes a weight change
AND:   scores 10 posts with the new weights
AND:   if approval-correlation improves: git commit weights, update research.md
AND:   if regression: git revert, log to research/{slug}/research_log.md
AND:   after 5 consecutive failures: shift strategy (weight-tuning → hook-pattern analysis)
TEST:  tests/autoresearch/test_ab_loop.py (NEW) — asserts the ratchet only
       keeps improvements and reverts regressions.
```

### PHASE D — Voice control

**D.1 TELEGRAM_SPEC**
```
GIVEN: TELEGRAM_BOT_TOKEN + TELEGRAM_USER_ID set, bot registered via @BotFather
WHEN:  Stavarai sends /status to the bot
THEN:  bot returns real pipeline status
WHEN:  anyone else sends any command
THEN:  bot returns NOTHING (not even an error)
WHEN:  Stavarai sends a voice note
THEN:  Whisper transcribes → intent parsed → command executed → text reply
TEST:  tests/telegram/test_bot_commands.py (NEW) — asserts is_stavarai()
       silences non-matching user IDs.
```

**D.2 VISIONCLAW_SPEC** (Meta glasses)
```
GIVEN: glasses configured to POST to /api/voice/command with VISIONCLAW_WEBHOOK_SECRET
WHEN:  Stavarai says "run pipeline for cella coffee"
THEN:  transcript parsed → intent=run_pipeline, entity=cella-coffee
AND:   Hermes executes → TTS response plays through the glasses
TEST:  tests/voice/test_visionclaw_integration.py (NEW).
```

### PHASE E — Public surfaces to production

**E.1 VERCEL_SPEC**
```
GIVEN: VERCEL_TOKEN + VERCEL_PROJECT_ID set
WHEN:  cd frontend && vercel deploy --prod
THEN:  0 build errors
AND:   / renders landing, /blog renders 7 posts, /admin gates on BLASTER2026
AND:   NEXT_PUBLIC_DEMO_MODE=false in Vercel env (production calls the VPS API)
TEST:  curl the deployed URLs, assert 200 + expected text fragments.
```

**E.2 ACCESSIBILITY_SPEC** (arXiv accessible HTML — non-negotiable)
```
GIVEN: any page
THEN:  all images have alt text, all inputs have labels, color contrast ≥ 4.5:1,
       keyboard nav works, focus visible, skip-to-content link present, <html lang>
TEST:  axe-core scan in CI (extend test-api.yml or add a11y job). Zero critical violations.
```

---

## 4. Hard guardrails (violating any of these stops the build)

1. **Never commit `.env`, never log `BLASTER2026` or any API key.**
   The auth test already asserts the password isn't logged — keep it green.
2. **Never mix client data.** Every query must scope to `schema_{slug}`.
   The isolation test must stay green after every change.
3. **Never hardcode a model name.** All LLM calls go through `services/llm_adapter.py`.
4. **Never publish without human approval.** No auto-publish, ever.
   The approval queue is the gate; the publisher only fires on explicit approve.
5. **Never expose internal names publicly.** "Stavarai", "Hermes", "Buffer Blaster"
   appear ONLY in `/admin/*` and internal docs. The landing page and blog use
   neutral brand voice ("the team", "the system").
6. **One bead per destructive op.** Schema changes, deploys, weight commits,
   data migrations — each writes `.beads/{timestamp}_{action}.bead` first.
7. **Tests before code.** Every new feature ships with a failing test that
   passes after implementation. No exceptions.
8. **Production writes require the service key.** The anon key is read-only on
   published blog posts and nothing else.

---

## 5. The 7 gaps that need human input (Stavarai must provide)

| # | Gap | Where it goes | Blocks |
|---|---|---|---|
| 1 | `SUPABASE_PROJECT_REF` + service key | `.env` | Phase B |
| 2 | `VERCEL_PROJECT_ID` + token | `.env` | Phase E.1 |
| 3 | Telegram bot token + Stavarai's user ID | `.env` + @BotFather | Phase D.1 |
| 4 | VisionClaw glasses config | glasses → VPS webhook | Phase D.2 |
| 5 | `FIRECRAWL_API_KEY` | `.env` | URL scanning |
| 6 | `HIGGSFIELD_API_KEY` | `.env` | Video generation |
| 7 | First client's historical content data | `schema_{slug}` | Autoresearch loop (Phase C.3) |

Until #7 lands, the autoresearch loop runs on competitor-outlier data as a proxy
(cold-start fallback, documented in `docs/GAPS.md`).

---

## 6. Skills to load (already in `skills/`, copy to `~/.hermes/skills/` on VPS)

| Skill | Purpose | Source |
|---|---|---|
| `grill-me` | One-question-at-a-time client intake → `brief.yaml` | `skills/grill-me/SKILL.md` |
| `stop-slop` | Anti-AI-writing guardrail on every text output | `skills/stop-slop/SKILL.md` |
| `food-beverage` | Seedance 2.0 cinematics, 10 hook types | `skills/food-beverage/SKILL.md` |
| `ugc-video` | Sirio Berati A/B prompt format (beauty/apparel/home) | `skills/ugc-video/SKILL.md` |
| `scoring` | 6-dimension viral scoring → JSON | `skills/scoring/SKILL.md` |
| `claude-handoff` | This format (state/decisions/next/gaps) | `willseltzer/claude-handoff` |

---

## 7. Remote repos to connect (clone to /opt on the VPS)

| Repo | Why | Path |
|---|---|---|
| `NousResearch/hermes-agent` | The orchestrator that runs the pipeline | `/opt/hermes` |
| `knowsuchagency/mcp2cli` | Expose Higgsfield MCP as a CLI bridge | `/opt/mcp2cli` |
| `Intent-Lab/VisionClaw` | Meta Ray-Ban glasses voice integration | `/opt/visionclaw` |
| `earendil-works/absurd` | Long-running-task resilience / retry | pip install |
| `karpathy/autoresearch` | Pattern source for the A/B scoring loop | reference |
| `executiveusa/pauli-taste-skill` | Taste rubric for design QA (gated) | `/opt/pauli-taste` |

---

## 8. Definition of done (production)

- [ ] `cargo test` green on VPS (Rust core proven)
- [ ] `python -m pytest tests` green including the new live-Supabase + RLS tests
- [ ] `cd frontend && npm run build` → 0 errors, axe-core 0 critical
- [ ] Vercel prod deploy live, `DEMO_MODE=false`, calls VPS API
- [ ] `/api/health` reports `"core": "rust"`
- [ ] One real client onboarded end-to-end: interview → pipeline → approval → Buffer publish
- [ ] Telegram `/status` returns real data; voice note executes a command
- [ ] Autoresearch loop ran one full night, wrote at least one `research_log.md` entry
- [ ] `.beads/` shows the full production bring-up sequence, all reversible
- [ ] Zero instances of internal names on public surfaces (grep the built `.next` if unsure)

---

## 9. If you get stuck

- **Rust won't compile on the VPS:** install `build-essential` + `libssl-dev`,
  re-run `cargo test`. Do NOT fall back to Python silently — the `/api/health`
  `core` field must honestly report which backend is live.
- **Hermes spawn tree too deep / too costly:** cap `HERMES_MAX_CHILDREN=10` and
  `max_spawn_depth=3` (already set). Document the cost in `docs/GAPS.md`.
- **A public surface accidentally leaks an internal name:** grep
  `frontend/src` and `content/blog` for "hermes|buffer.?blaster|stavarai"
  (case-insensitive). Fix before any deploy.
- **A test is flaky on the VPS but green locally:** the rate-limiter and
  session tests are timing-sensitive. Use `time.monotonic()` (already do) and
  widen tolerances, never disable the test.

When in doubt: **simpler, faster, more private.** The acquisition thesis depends
on the company depending on the *output*, never seeing the engine.

---

*Begin at Phase A.1. Write the bead before every destructive op. Tests first.*
