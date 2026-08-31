# 06_handoff — return verified result to Hermes

One job: package the experiment result for Hermes/Pauli commercial action without duplicating sales state inside Buffer Blaster.

## Inputs
- Working: ../05_decide/output/decision.md
- Working: ../04_ingest/output/measurement-summary.md
- Reference: API money-loop contract at `/api/studio/money-loop/contract`

Do NOT load: unrelated prospect CRM history or private client data outside this experiment.

## Process
1. Return experiment ID, proof asset IDs, judge receipts, decision, winner ID, performance evidence, attribution evidence, spend, and rollback/stop state.
2. Map PASS to a recommended commercial next step; map ITERATE/KILL/HOLD to the reason and next bounded action.
3. Leave outreach, proposal, close, and memory promotion to Hermes/Pauli.

## Outputs
- hermes-result.md → output/

## Human check
Confirm the handoff contains only verified claims supported by the experiment evidence and no client-private data beyond the authorized opportunity scope.
