# Phase 05 — Buffer / Shopify / REST / MCP / CLI interoperability

- [ ] Verify current Buffer publishing adapter and Shopify attribution/webhook contracts before modifying them.
- [ ] Make Buffer Blaster the creative/control layer and Buffer an optional downstream distribution adapter; do not duplicate Buffer's scheduling product.
- [ ] Prove Shopify product/context intake can feed Buffer Blaster without leaking client data across workspaces.
- [ ] Ensure the same high-value operations are callable through REST, MCP and CLI with consistent identifiers and receipts.
- [ ] Add remote-agent examples for create-plan, status/readback, export/publish-preparation and attribution readback.
- [ ] Verify unauthenticated MCP/REST consequential operations fail closed.
- [ ] Add contract tests for interface parity and provider-disabled behavior.

Exit: an approved remote agent can move product/context into Buffer Blaster, prepare creative, read receipts and hand approved output toward Buffer/Shopify flows without bypassing governance.