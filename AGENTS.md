# AGENTS.md — Buffer Blaster Router

**Where am I?** Buffer Blaster is private creative infrastructure used to research, produce, approve, and learn from client ad creative. It is not positioned as a low-ticket public SaaS subscription.

## Start here
1. Read `CONTEXT.md` for the product map and task routing.
2. Read `EMERALD_TABLETS.md` for non-negotiable engineering rules.
3. Read only the `CONTEXT.md` for the area you are changing.

## Task routing
| Task | Read next |
|---|---|
| Public site / Studio UI | `frontend/CONTEXT.md` |
| API / auth / integrations | `api/CONTEXT.md` |
| CLI / remote agent use | `cli/CONTEXT.md` |
| Database / RLS / migrations | `supabase/CONTEXT.md` |
| Deploy / production proof | `docs/PRODUCTION.md` + `GATES.production.md` |
| Product boundaries | `docs/APP_BOUNDARIES.md` |
| Agent interfaces | `docs/AGENT_INTERFACES.md` |
| Current positioning | `docs/POSITIONING.md` |

## Canonical interfaces
- UI: `frontend/`
- REST: `/api/studio/*`
- MCP: `/api/mcp`
- CLI: `python -m cli.blaster`
- Voice: `/api/voice/command`
- Database: self-hosted Supabase, schema `buffer_blaster`

## Human gates
Agents may research, draft, prepare, test, and verify. Paid generation, publishing, ad activation, destructive operations, and contractual commitments require the repository's explicit approval controls. Never bypass them.

## Repository law
- Default branch: `main`; squash merge.
- Tests and evidence before completion claims.
- Secrets live only in runtime environment stores.
- No client-data mixing.
- No hardcoded provider/model IDs.
- Do not merge another application's identity, data, secrets, or runtime into Buffer Blaster.
- Use the smallest change that produces verified value.
