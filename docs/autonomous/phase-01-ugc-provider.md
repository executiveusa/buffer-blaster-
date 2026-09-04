# Phase 01 — UGC provider + provenance contract

- [x] Read AGENTS.md, CONTEXT.md, api/CONTEXT.md, frontend/CONTEXT.md, EMERALD_TABLETS.md.
- [x] Inspect current UGC/Fal provider code and tests before adding abstractions.
- [x] Study OpenShorts, Open-AI-UGC, Lazynext and record useful patterns plus license/provenance in docs/UGC_OPEN_SOURCE_RESEARCH.md.
- [x] Define one provider-neutral UGC job contract covering input assets, actor/reference, script, format, provider/model, estimated cost, approval state, output receipt, failure state.
- [x] Preserve existing Fal behavior behind the contract; no hardcoded model IDs in UI/business logic.
- [x] Add deterministic tests for provider selection, approval-before-paid-generation, receipts and failure handling.
- [x] Prove existing production APIs remain backward compatible or document an intentional migration path.

Exit: all tasks checked, Python tests green, frontend lint/build green if touched, no new secret surface.

## Machine proof notes

- `FalVideoProvider.submit_video` and `fetch_url` remain unchanged as backwards-compatible methods.
- New `plan_job` / `submit_job` methods use `UGCProviderJob`; no provider call occurs while approval is absent or estimated cost exceeds the job ceiling.
- Provider/model identifiers remain runtime configuration under `api/services/media_generation.py`.
- No schema, frontend, publishing, wallet or secret surface changed in this phase.
