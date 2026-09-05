# Phase 04 — Long-form to short-form repurposing

- [x] Inspect existing media ingestion/export/transcript capabilities before adding anything.
- [x] Study AI-Youtube-Shorts-Generator and OpenShorts clipping flows for highlight detection, crop, captions and batch patterns.
- [x] Add a provider-neutral repurpose plan: source media -> transcript/reference -> ranked moments -> vertical clip plans -> captions/b-roll instructions.
- [x] Reuse existing media storage and job/receipt infrastructure.
- [x] Keep actual paid generation/render behind existing approval and wallet controls.
- [x] Add REST/MCP/CLI plan/readback parity for agent-driven repurposing.
- [x] Add deterministic fixtures/tests so no external model spend is required in CI.

Exit: one long-form input can deterministically produce ranked governed short-form plans through agent-callable interfaces.

Machine evidence is implemented on branch `autofinish/phase-04-repurpose`; merge remains contingent on full repository CI for the frozen head.
