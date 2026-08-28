# AGENTS.md — Operating Contract

> Read `EMERALD_TABLETS.md` first. It overrides this file. Orchestrator: GRINIONS™ v1.

## Identity

- Internal platform: **Stavarai Platform**.
- Repository codename: **Buffer Blaster**.
- Public product surfaces use neutral **Social Studio** language; internal codenames remain out of `/`, `/pricing`, `/blog/**`, and public metadata.
- Purpose: agent-first content operations for brands and agencies — campaign planning, UGC creation, scoring, approval, scheduling, analytics, and learning.
- Repository: `https://github.com/executiveusa/buffer-blaster-`.
- Default branch: `main`; squash-merge only; never force-push `main`.

## V1 architecture

```text
frontend/                 Next.js product + public site
api/                      FastAPI operational backend
api/services/             provider-neutral UGC, Social Drop, publishing, voice
plugins/social-studio/     portable agent skill/plugin
cli/                       scriptable operator client
rust_core/                 security/runtime primitives with Python fallback
supabase/                  existing migrations and isolation boundary
skills/                    reusable creative/quality skills
openspec/                  accepted change contracts
ops/                       receipts and rollback evidence
```

TryPost is a replaceable external publishing kernel accessed over REST. It is not vendored into this proprietary repository. Fal is a replaceable media provider. Model IDs and provider credentials are environment-driven.

## Agent interfaces

- REST: `/api/studio/*`
- MCP: `/api/mcp`
- CLI: `python -m cli.blaster`
- Plugin: `plugins/social-studio/SKILL.md`
- Voice: `/api/voice/command`

All interfaces share the same human approval gate for scheduling and publishing.

## Database

Existing project and isolation rules remain authoritative. V1 does not require a destructive database migration. Do not mix client data; retain schema-scoped access and current RLS rules.

## Secrets

Never store secret values in the repository, chat logs, issues, screenshots, or public docs. Provider tokens are runtime environment variables only. Relevant V1 names are documented in `.env.example`.

## Working agreement

1. Verify before claiming completion.
2. Tests before implementation.
3. One accepted OpenSpec change = one PR.
4. Squash-merge only.
5. No public internal codenames.
6. No public publishing without explicit human approval.
7. No hardcoded LLM or media model IDs in runtime code.
8. Every deploy/destructive op gets bead + rollback evidence first.
9. Do not bypass CI, RLS, auth, or secret controls to ship faster.
10. Use the smallest change that produces real evidence.
