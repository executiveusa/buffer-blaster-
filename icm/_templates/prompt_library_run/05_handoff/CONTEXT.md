# 05 Handoff

## Job
Deliver the approved prompt package into the consuming workflow.

## Routes
- UGC ad production: hand the package to `icm/_templates/ugc_ad_factory/` stage `04_generate` (provider-neutral generation boundary; clip 1 then clip 2 from the approved seed frame).
- Portable agent use: export via `python3 scripts/icm_bundle.py` and ship the bundle.
- Direct Studio/API use: attach the package to the campaign brief so the operator sees prompt, provenance, benchmark, and approval together.

## Rules
- The package is the unit of handoff: adapted prompt + provenance + benchmark verdict + approval artifact. Never hand off a bare prompt.
- Cost and quote metadata stay estimates until reconciled against actual receipts in the consuming workflow.

## Output
`output/handoff.md` — destination workflow, package contents, and the receiving stage/owner.
