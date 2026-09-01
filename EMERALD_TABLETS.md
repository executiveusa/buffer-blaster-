# EMERALD_TABLETS.md — The Non-Negotiables

> Highest layer of governance. Overrides everything else in this repo,
> including `AGENTS.md`, accepted specs, and agent preference. Mirrors the
> GRINIONS™ v1 prime directive: **Verify It Before Everything (V.I.B.E.)**.

## Tier 1 — Identity (never change without owner sign-off)

1. **Canonical product name: Buffer Blaster.** Until the owner chooses the next
   product name, all current product/operator identity uses **Buffer Blaster**.
   Historical/internal implementation labels such as "Stavarai", "Hermes", and
   provider names must not leak onto public marketing surfaces unless explicitly
   required by the product experience.
2. **One operator security boundary.** No public production console. Live
   operator access requires a runtime-generated/configured `DEMO_PASSWORD` or
   `BLASTER_API_KEY`; there is no committed, fallback, or well-known production
   password. Installation generates app-owned credentials locally when blank.
3. **Built to sell.** Every architectural decision must make the platform more
   acquirable: teachable, unique, repeatable. See `docs/BUILT_TO_SELL.md`.

## Tier 2 — Data & Security

4. **No client/workspace data mixing.** Workspace/client ownership must be
   enforced below presentation code. Service-role queries bypass RLS, so they
   MUST include the canonical workspace scope explicitly. Any isolation change
   requires a regression test.
5. **Production writes require the service key.** The anon key is read-only on
   explicitly public data and nothing else. RLS is enabled on canonical tables;
   service-role code must still enforce workspace ownership because it bypasses RLS.
6. **Never log or commit secrets.** Passwords, API keys, service-role keys,
   session secrets, and provider credentials may not appear in stdout, stderr,
   commits, error messages, analytics, documentation examples, or deploy scripts.
7. **No auto-publish or auto-spend.** Publishing and paid-media mutation require
   explicit human approval. There is no approval bypass.

## Tier 3 — Engineering discipline

8. **Tests before code.** Every new feature ships with a failing test that
   passes after implementation. No disabling tests to pass — fix the test or
   fix the code.
9. **LLM-agnostic.** No hardcoded model names in runtime selection logic. Model
   provider/IDs stay environment-driven and route through the provider boundary.
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
14. **Rollback is proven before merge.** Every phase PR includes rollback
    evidence appropriate to its blast radius. No proven rollback → no merge.
15. **Stop-slop on all generated text.** No "AI-powered", "revolutionize",
    "unlock", "elevate", "leverage". See `skills/stop-slop/SKILL.md`.
16. **One canonical production path.** Backend deployment routes through
    `scripts/selfhost/install.sh`; Vercel live-mode setup routes through
    `scripts/selfhost/configure-vercel.sh`. Legacy entrypoints may delegate to
    these files but may not implement a second production configuration.

## Tier 5 — Operating tools (mandatory for autonomous agents)

17. **jcodemunch is the default retrieval layer** when available. Index once per
    session and retrieve symbols rather than dumping entire files into context.
18. **RTK prefixes CLI commands** when installed. See `scripts/install-tools.sh`.
19. **OpenCodeReview is the independent PR review gate.** Keep its reusable
    workflow pinned to a reviewed commit and treat material findings as release
    blockers until resolved or explicitly accepted with evidence.

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
