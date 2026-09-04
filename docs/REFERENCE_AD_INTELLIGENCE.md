# Reference-ad intelligence

Buffer Blaster may analyze a reference ad only when the operator supplies a source with `owned`, `licensed`, or `authorized_analysis` rights state. The reference is evidence for **creative mechanics**, not a template to copy.

## What is retained

The canonical receipt stores source provenance and hash plus mechanic labels:

- hook mechanic
- customer problem/tension
- promise/mechanism structure
- proof device
- CTA mechanic
- pacing
- normalized shot purposes
- originality transformations
- claims/brand risks

The reference transcript and raw shot descriptions are used for deterministic classification but are not written into the strategy receipt. `CreativeSource.metadata.reference_copy_stored=false` and `StrategyReceipt.metadata.reference_copy_stored=false` make that boundary explicit.

## Remix output

One authorized analysis produces exactly three no-spend UGC plan receipts:

1. `control` — preserves the observed mechanic ordering at an abstract level.
2. `challenger_hook` — changes the opening order.
3. `challenger_proof` — moves proof/demonstration forward.

Every script is generated from the client product, audience and operator-approved claims. Protected reference-brand terms are rejected if they appear in generated copy. Each plan is `approval_state=draft` with `estimated_cost_ceiling_cents=0`; this phase cannot invoke a media provider or reserve wallet spend.

## Idempotency

`idempotency_key` is unique inside a workspace. The receipt also stores a deterministic request fingerprint. Repeating the same request replays the same strategy and plan IDs. Reusing the key with materially different client/remix inputs returns `idempotency_conflict`.

## Interfaces

REST:
- `POST /api/studio/reference-ads/analyze`
- `GET /api/studio/reference-ads/strategy/{receipt_id}`

MCP:
- `analyze_reference_ad`
- `get_reference_strategy`

CLI:
```bash
python -m cli.blaster reference-analyze reference.json
python -m cli.blaster reference-strategy <receipt-id>
```

All three interfaces use the same canonical service and operator authentication boundary.
