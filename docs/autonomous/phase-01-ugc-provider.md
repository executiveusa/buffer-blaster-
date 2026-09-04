# Phase 01 — UGC provider + provenance contract

- [ ] Read AGENTS.md, CONTEXT.md, api/CONTEXT.md, frontend/CONTEXT.md, EMERALD_TABLETS.md.
- [ ] Inspect current UGC/Fal provider code and tests before adding abstractions.
- [ ] Study OpenShorts, Open-AI-UGC, Lazynext and record useful patterns plus license/provenance in docs/UGC_OPEN_SOURCE_RESEARCH.md.
- [ ] Define one provider-neutral UGC job contract covering input assets, actor/reference, script, format, provider/model, estimated cost, approval state, output receipt, failure state.
- [ ] Preserve existing Fal behavior behind the contract; no hardcoded model IDs in UI/business logic.
- [ ] Add deterministic tests for provider selection, approval-before-paid-generation, receipts and failure handling.
- [ ] Prove existing production APIs remain backward compatible or document an intentional migration path.

Exit: all tasks checked, Python tests green, frontend lint/build green if touched, no new secret surface.