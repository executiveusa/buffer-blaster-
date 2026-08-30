# Tasks — wiring-truth-pricing-v2

## Tests first
- [ ] Add pricing/margin guard tests.
- [ ] Add Fal URL-origin security tests.
- [ ] Add UGC execution coordinator fixture tests.
- [ ] Add voice/factory parity regression test.
- [ ] Add settings handshake semantics tests.
- [ ] Add migration ordering/clean-chain structural test.
- [ ] Extend frontend gauntlet to reject synthetic production state and stale checkout metadata.

## Backend truth / security
- [ ] Restrict credential-bearing Fal fetches to configured queue origin.
- [ ] Repair pipeline cancel path.
- [ ] Replace integration env-presence `connected` claims with configured/verified states.
- [ ] Make settings update semantics truthful and durable for supported operator settings.
- [ ] Align voice UGC command with the factory plan service.

## UGC execution
- [ ] Add provider-neutral factory execution coordinator.
- [ ] Add ffmpeg runtime dependency.
- [ ] Add provider result extraction/download helpers.
- [ ] Add trim, seed-frame, seam QA, stitch helpers.
- [ ] Add durable execution receipt state.
- [ ] Expose execution status through REST and MCP without bypassing human approval.

## Canonical state / UI
- [ ] Remove hardcoded live Studio metrics or replace with real status/empty state.
- [ ] Remove hardcoded Library queue or mark it non-live until backed by ledger.
- [ ] Remove synthetic analytics claims; show evidence-required empty state.
- [ ] Remove stale TryPost operational claims from Canvas/plugin surfaces.
- [ ] Make dead Canvas/Moodboard controls visibly disabled unless execution exists.

## Database
- [ ] Repair duplicate migration numbering without changing already-applied SQL semantics.
- [ ] Add self-contained Buffer Blaster canonical production tables before beta indexes.
- [ ] Add clean migration-chain proof.

## Pricing / checkout
- [ ] Add server-side pricing package and margin guard contract.
- [ ] Add 7-day paid trial and 30-day paid trial offers.
- [ ] Connect current offer CTAs to the correct Stripe checkout route.
- [ ] Retire stale Founding Creator checkout metadata from current pricing path.
- [ ] Ensure credit grant cannot exceed configured provider-cost budget or margin floor.
- [ ] Add exact pre-render cost/credit requirement to the execution receipt.

## Interface parity
- [ ] Add factory plan/render/status commands to CLI.
- [ ] Update plugin to the current factory/MCP contract.
- [ ] Ensure voice points at the same UGC factory path as UI/MCP.

## Proof
- [ ] Run Python tests.
- [ ] Run frontend gauntlet/lint/build/route smoke.
- [ ] Run production Docker build/smoke.
- [ ] Verify Vercel preview.
- [ ] Keep paid live provider render behind explicit approval; do not spend automatically in CI.
- [ ] Record rollback receipt.
