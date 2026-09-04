# Phase 04 — Long-form to short-form repurposing

- [ ] Inspect existing media ingestion/export/transcript capabilities before adding anything.
- [ ] Study AI-Youtube-Shorts-Generator and OpenShorts clipping flows for highlight detection, crop, captions and batch patterns.
- [ ] Add a provider-neutral repurpose plan: source media -> transcript/reference -> ranked moments -> vertical clip plans -> captions/b-roll instructions.
- [ ] Reuse existing media storage and job/receipt infrastructure.
- [ ] Keep actual paid generation/render behind existing approval and wallet controls.
- [ ] Add REST/MCP/CLI plan/readback parity for agent-driven repurposing.
- [ ] Add deterministic fixtures/tests so no external model spend is required in CI.

Exit: one long-form input can deterministically produce ranked governed short-form plans through agent-callable interfaces.