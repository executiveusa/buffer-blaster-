# Phase 02 — Reference-ad intelligence + remix

- [x] Inspect current research/creative-angle/brief pipelines and reuse existing entities.
- [x] Study Lazynext reference-ad workflows and OpenShorts creative flow; record patterns only.
- [x] Add a reference-ad intake path that stores source/provenance and extracts hook, problem, promise, proof, CTA, pacing and shot structure without copying protected brand identity.
- [x] Add a client-product remix plan that creates at least control + two challenger concepts from the extracted strategy.
- [x] Require human approval before any paid render.
- [x] Persist decision/provenance receipts so agents can explain why each variant exists.
- [x] Add REST and MCP coverage for plan/readback; CLI parity where appropriate.
- [x] Add deterministic tests for provenance, no-copy guardrails, idempotency and approval boundaries.

Exit: reference ad -> analysis -> three governed variant plans works without paid generation.

## Machine proof notes

- Analysis is deterministic and provider-free; no LLM or media generation import is present in `api/services/reference_ad.py`.
- `creative_sources` retains reference provenance/hash and explicitly marks analysis-only/no-copy storage.
- `strategy_receipts` stores only mechanic labels, source hashes, originality transformations, risks and linked variant IDs; migration 014 adds workspace replay metadata without destructive changes.
- Exactly three canonical UGC plans are produced: control, challenger_hook and challenger_proof. Each is `draft` with a zero-cent generation ceiling.
- Protected reference-brand terms are rejected from generated variant copy.
- REST, MCP and CLI resolve to the same service. Tests cover cross-interface readback, replay and idempotency conflict.
