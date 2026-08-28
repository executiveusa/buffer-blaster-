# Campaign Context Template

Job: carry one campaign from objective to approved publishing evidence.

## Working inputs

- `01_brief/output/brief.md`
- stage outputs produced later in this folder

## Reference inputs

- `../../_system/CONTEXT.md`

## Process

1. `01_brief` defines objective, audience, offer, platforms, dates, and constraints.
2. `02_create` produces editable copy/media briefs/UGC prompts and scored variants.
3. `03_review_publish` records human decisions, schedule payloads, publisher receipts, and results pointers.

## Outputs

All outputs remain plain human-editable files in the stage `output/` folders. Provider job IDs and publishing receipts are evidence; secret values never enter this workspace.

## Human check

A person must read the creative output before approval. Public scheduling/publishing is blocked until the review stage records explicit approval.
