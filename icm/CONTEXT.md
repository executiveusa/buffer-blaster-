# Social Studio ICM

Purpose: route a cold agent into the smallest context needed to create social work or run a measured proof-first experiment.

## Where things live

- Stable factory rules and interface contracts: `_system/CONTEXT.md`
- Blank repeatable campaign: `_templates/campaign/CONTEXT.md`
- Blank repeatable measured experiment: `_templates/experiment/CONTEXT.md`
- Live campaigns/experiments: instantiated product folders when created
- Provider/runtime code stays in the repository; ICM stores human-editable state and stable evidence pointers, not secrets or bulk provider payloads.

## Routes

### Content campaign
`01_brief → 02_create → 03_review_publish`

Use when the deliverable is social content/campaign production.

### Proof-first money-loop experiment
`01_define → 02_bind_channels → 03_launch → 04_ingest → 05_decide → 06_handoff`

Use when a proof asset must be tested against a business KPI and returned to Hermes/Pauli with verified performance/attribution evidence.

Status is derived from the artifacts present in each stage `output/` directory. Public publishing/spend is legal only when the applicable stage contains an explicit human approval artifact.

## Cold-agent route

1. Read root `AGENTS.md`.
2. Read this file.
3. Read the selected template/instance `CONTEXT.md` and only the current stage contract.

Do not load unrelated campaigns/experiments or duplicate facts across stages; link to the one authoritative home instead.
