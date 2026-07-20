# Change: add-production-bringup

## Status

`proposed` — awaiting owner acceptance. Once accepted, this file (not chat)
is the source of truth for the production bring-up.

## Summary

Take the working demo-grade codebase (frontend + FastAPI + Rust core + Supabase
migrations, currently green on `main`) and harden it for production on a Linux
VPS + Vercel. Delivers the live pipeline, voice control, and public surfaces.

## Motivation

The platform is built and the demo runs anywhere, but none of it is live.
The acquisition thesis depends on the company *depending on the output* —
which requires the pipeline to actually run, score, and publish on real
client data, with the operator controlling it by voice and dashboard.

This change is the bridge from "demo we can show" to "engine the company
can't replace".

## Scope

**In scope:**
- Phase A — VPS bring-up (push CI workflows, prove Rust core, drop prebuilt lib)
- Phase B — Live Supabase (migrations, RLS verification, repository layer)
- Phase C — Live pipeline (Hermes install, E2E pipeline spec, autoresearch loop)
- Phase D — Voice control (Telegram bot, VisionClaw Meta glasses)
- Phase E — Public surfaces to production (Vercel deploy, accessibility gate)

**Out of scope (file separate changes):**
- Buffer API live publishing integration (Phase E.5, follow-up)
- Email provider selection and integration (Phase E.6, follow-up)
- Affiiate link activation (post-acquisition)

## Risks

| Risk | Tier | Mitigation |
|---|---|---|
| Rust core diverges from Python fallback contract | high | Both must pass the parity tests; `/api/health` honestly reports which backend |
| Cross-client data leak via Supabase | high | RLS test (`tests/clients/test_rls_isolation.py`) required before Phase B merges |
| Auto-publish fires without approval | high | No code path exists; add a contract test in Phase C that asserts the publisher requires an Approve event |
| Internal name leaks to public surface | medium | Grep gate in CI: `grep -riE 'stavarai\|hermes\|...' frontend/src content/blog` |
| Telegram bot responds to non-operator | high | `is_stavarai()` test required; bot returns NOTHING for other user IDs |
| Vercel deploys with DEMO_MODE=true | medium | CI asserts `NEXT_PUBLIC_DEMO_MODE=false` in the Vercel env on prod deploys |

## Acceptance criteria

Mirrors `docs/HANDOFF.md` §8 "Definition of done". All gates must be green
and the rollback contract for each phase must be tested before merge.

## References

- `docs/HANDOFF.md` (the phase-by-phase TDD roadmap)
- `docs/BUILT_TO_SELL.md` (acquisition framing)
- `EMERALD_TABLETS.md` (non-negotiables)
- `openspec/specs/production-readiness/spec.md` (durable capability spec)
