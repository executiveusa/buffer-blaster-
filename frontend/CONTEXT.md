# Frontend CONTEXT

## Inputs
- Product positioning: `docs/POSITIONING.md`
- Product boundaries: `docs/APP_BOUNDARIES.md`
- API contract: `docs/AGENT_INTERFACES.md`
- Shared design rules: `EMERALD_TABLETS.md`

## Job
Render the public Buffer Blaster site and the human Studio without exposing backend complexity or secrets. Public identity is **Buffer Blaster**; **Studio** is the workspace.

## Outputs
- `src/app/` routes and page states
- `src/components/` reusable interaction pieces
- browser-visible calls through approved API boundaries

## Human check
At 320, 375, 390, 430, 768, 1024, and 1440 widths: no horizontal overflow, clear primary action, readable contrast, accessible focus, deliberate mobile ordering, no false success claims, and no secret/client-data exposure.
