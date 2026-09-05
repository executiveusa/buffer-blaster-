# Phase 05 — Buffer / Shopify / REST / MCP / CLI interoperability

- [x] Verify current Buffer publishing adapter and Shopify attribution/webhook contracts before modifying them.
- [x] Make Buffer Blaster the creative/control layer and Buffer an optional downstream distribution adapter; do not duplicate Buffer's scheduling product.
- [x] Prove Shopify product/context intake can feed Buffer Blaster without leaking client data across workspaces.
- [x] Ensure the same high-value operations are callable through REST, MCP and CLI with consistent identifiers and receipts.
- [x] Add remote-agent examples for create-plan, status/readback, export/publish-preparation and attribution readback.
- [x] Verify unauthenticated MCP/REST consequential operations fail closed.
- [x] Add contract tests for interface parity and provider-disabled behavior.

Exit: an approved remote agent can move product/context into Buffer Blaster, prepare creative, read receipts and hand approved output toward Buffer/Shopify flows without bypassing governance.

Machine evidence is implemented on branch `autofinish/phase-05-interoperability`; merge remains contingent on full repository CI for the frozen head.
