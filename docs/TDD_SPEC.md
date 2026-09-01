# TDD_SPEC.md — Archived legacy specification

This file previously described the pre-Buffer-Blaster Stavarai/Postatees
architecture, including a well-known demo password, per-client schema creation,
hardcoded model examples, and implementation paths that no longer match the
current application.

It is retained only as an archive marker. **Do not implement from the former
contents.**

## Current test-first contract

1. Read `EMERALD_TABLETS.md` and `AGENTS.md`.
2. Route through `icm/CONTEXT.md` and the accepted OpenSpec for the active change.
3. Inspect the current implementation before adding code.
4. Write a failing regression test for the behavior being changed.
5. Implement the smallest verifiable repair.
6. Run the affected tests plus the full repository CI gate before merge.
7. Record rollback evidence for destructive/deployment changes.

## Current runtime invariants

- Canonical product name: **Buffer Blaster**.
- No committed/default production password.
- Production state uses the canonical `buffer_blaster` Supabase schema.
- Service-role queries explicitly enforce workspace ownership because service
  role bypasses RLS.
- Provider/model IDs are environment-driven.
- Rust is optional; Python fallback remains supported.
- Publishing and paid-media mutation require explicit human approval.
- Production deployment uses only `scripts/selfhost/install.sh` and
  `scripts/selfhost/configure-vercel.sh`.

Current tests live under `tests/` and are the executable specification. Current
material design changes live under `openspec/changes/`; current campaign and
experiment state lives under `icm/`.
