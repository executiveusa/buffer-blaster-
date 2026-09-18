# 04 Gate

## Job
Human approval before anything paid or public.

## Rules
- Present the adapted prompt, its benchmark verdict, the estimated generation cost, and the provenance header as one review package.
- Approval must be an explicit human artifact in this stage's `output/` (approval note, signed comment, or linked approval message). Verbal-in-chat approvals are recorded with source and timestamp.
- No approval artifact, no generation. This gate cannot be skipped by agents.

## Output
`output/approval.md` — approver, timestamp, scope approved (what may be generated, cost ceiling), and the exact prompt hash approved.
