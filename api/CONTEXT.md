# API CONTEXT

## Inputs
- Runtime env: `.env.production` / environment store (never commit values)
- Schema contract: `supabase/CONTEXT.md`
- App boundaries: `docs/APP_BOUNDARIES.md`
- Interface contract: `docs/AGENT_INTERFACES.md`

## Job
Provide the canonical governed backend for Studio, agents, providers, approvals, attribution, and production receipts. The browser and agents must reach the same authoritative services.

## Outputs
- authenticated API responses
- durable records in self-hosted Supabase
- provider requests only after configured safety/approval checks
- explicit errors instead of fabricated success

## Human check
Verify unauthenticated privileged routes fail closed, workspace isolation holds, no secret values are returned, paid/publish actions require approval, provider identity is verified before live use, and tests cover every changed contract.
