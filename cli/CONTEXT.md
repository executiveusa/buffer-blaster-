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
