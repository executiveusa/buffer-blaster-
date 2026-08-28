# Stage 03 — Review & Publish

Job: convert reviewed creative into an explicit approval decision, schedule payload, and publisher evidence.

## Reads

Working: `../01_brief/output/brief.md`, `../02_create/output/content.md`, optional UGC/render receipts.
Reference: `../../../_system/CONTEXT.md` and the Social Studio plugin contract.

## Process

Present final copy/media/platform/timing to the human. Record approval or revision. Only an explicit approved state may be sent to the publishing adapter. Resolve actual social-account IDs from the publisher; never invent them.

## Writes

- `output/approval.md` — approver, decision, timestamp, notes
- `output/schedule.json` — canonical Social Drop payload without secrets
- `output/publish-receipt.json` — normalized external ID/status/timestamps after a successful publisher call

## Human check

The human is the publish gate. `approved: true` must be explicit. If revision is requested, return to Stage 02 rather than mutating approved evidence in place.
