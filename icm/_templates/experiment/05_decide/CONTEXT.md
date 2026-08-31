# 05_decide — determine pass iterate or kill

One job: apply the predeclared thresholds to normalized evidence and produce a deterministic decision.

## Inputs
- Working: ../01_define/output/experiment.md
- Working: ../04_ingest/output/measurement-summary.md
- Reference: `api/services/experiment_engine.py`

Do NOT load: aesthetic opinions as substitutes for measured results.

## Process
1. Verify the minimum sample floor and attribution window are satisfied.
2. Evaluate each control/variant on the primary KPI.
3. Return HOLD, PASS, ITERATE, or KILL from the deterministic engine.
4. Record winner only on PASS; preserve spend, control delta, and evidence refs.

## Outputs
- decision.md → output/

## Human check
Verify the engine used the agreed KPI, threshold, sample floor, and correct variant IDs. Do not override weak evidence with preference.
