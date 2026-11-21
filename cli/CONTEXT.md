# CLI CONTEXT

## Inputs
- API base URL and operator credentials from runtime environment
- Interface contract: `docs/AGENT_INTERFACES.md`

## Job
Provide a scriptable remote control surface for approved operators and agents without duplicating backend logic. The CLI is a client of the canonical API, not a second orchestrator.

## Outputs
- machine-readable command results
- non-zero exit on failure
- no secret values in normal output

## Human check
Verify the CLI can call health/status and one safe read operation against production, requires authentication for privileged actions, preserves approval gates, and does not contain embedded credentials or provider-specific bypasses.

## Exception: `cli/render_local.py`
A one-shot operator render that runs the canonical planner and executor
in-process (no second orchestrator) for a single machine without Redis or
Supabase. It replaces the wallet with a required `--approve-cents` cap that
must cover the quote, reads `FAL_KEY` only from the environment, and never
prints it. See `docs/PRODUCTION.md`.
