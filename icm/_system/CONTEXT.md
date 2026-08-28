# Factory Context

Job: hold stable campaign rules and pointers shared by every run.

## Inputs

- `../../AGENTS.md` — repository routing and safety rules
- `../../skills/ugc-video/SKILL.md` — UGC creative playbooks
- `../../plugins/social-studio/SKILL.md` — agent interface contract
- `../../openspec/changes/v1-agentic-social-studio/specs/agentic-social-studio/spec.md` — V1 capability contract

## Process

Use these references to interpret a campaign brief. Campaign-specific facts never live here.

## Outputs

None. This is factory/reference context only.

## Human check

If a stable product rule changes, update its one authoritative source and keep this file as a pointer. Never copy secrets or live campaign payloads into `_system/`.
