# Social Studio ICM

Purpose: route a cold agent into the smallest campaign context needed to plan, create, review, and publish social work.

## Where things live

- Stable factory rules and interface contracts: `_system/CONTEXT.md`
- Blank repeatable campaign: `_templates/campaign/CONTEXT.md`
- Live campaigns: `campaigns/<campaign-id>/` when instantiated
- Provider/runtime code stays in the repository; this workspace stores human-editable campaign state and pointers, not secrets.

## Workflow

A campaign instance is copied from `_templates/campaign/` and moves through:

`01_brief → 02_create → 03_review_publish`

Status is derived from the artifacts present in each stage `output/` directory. Public publishing is legal only when the review stage contains an explicit human approval artifact.

## Cold-agent route

1. Read root `AGENTS.md`.
2. Read this file.
3. Read the target campaign `CONTEXT.md` and only the current stage contract.

Do not load unrelated campaigns or duplicate facts across stages; link to the one authoritative file instead.
