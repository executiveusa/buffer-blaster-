# Buffer Blaster

**Private creative infrastructure for client teams and AI agents.**

Buffer Blaster turns product truth, customer signals, and brand context into testable creative work. It keeps planning, UGC-style production, approvals, cost controls, and evidence in one governed system so operators can deliver more without making clients manage a pile of separate tools.

Buffer Blaster is not positioned as a low-cost public subscription. We use it inside managed client engagements or deploy a dedicated private instance when a team needs its own creative infrastructure.

## What it does

A normal creative loop is:

```text
product + customer context
        ↓
research and angles
        ↓
scripts / UGC production plan
        ↓
human review
        ↓
paid generation within server-owned limits
        ↓
asset + approval + cost evidence
        ↓
optional publishing / paid-media / commerce signals
        ↓
next iteration
```

Core capabilities include:

- campaign and creative planning;
- structured UGC-style video production;
- provider-neutral media generation;
- client/workspace persistence in self-hosted Supabase;
- server-owned generation-budget enforcement;
- explicit approval gates for paid generation and publishing;
- signed Shopify attribution/refund handling when a client connection is configured;
- paid-media experiment adapters for Meta and TikTok when account credentials are configured;
- optional downstream social publishing, including Buffer;
- the same governed workflow through the Studio UI, REST, MCP, and CLI.

## Access models

### Managed Creative Engine

We run Buffer Blaster as part of a client engagement. The client gets the creative output, review surface, visibility, and learning loop without becoming the administrator of another SaaS product.

### Private Install

A team can run a dedicated Buffer Blaster deployment with its own database boundary, provider credentials, Studio, API, MCP, and CLI access. Consequential actions remain governed by server-side approval and budget controls.

## Quick start

### Frontend development

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Useful routes:

- `/` — public product page
- `/studio` — creative workspace
- `/studio/create` — create a plan/batch
- `/admin` — operator console

### Full stack development

```bash
npm install
cd api && pip install -r requirements.txt && cd ..
npm run dev:local
```

Default local services:

- Next.js: `http://localhost:3000`
- FastAPI: `http://localhost:8000`

## Agent interfaces

All clients resolve to the canonical backend; none is a second orchestrator.

### REST

```text
GET  /api/health
GET  /api/studio/status
GET  /api/studio/jobs
POST /api/studio/...
```

### MCP

Endpoint:

```text
POST /api/mcp
```

It uses HTTP JSON-RPC 2.0 and operator Bearer authentication. Agents can plan without spend. Paid UGC execution still requires an active server-owned wallet and explicit approval.

### CLI

```bash
export BLASTER_API_URL=https://YOUR_API_HOST
export BLASTER_API_KEY=YOUR_OPERATOR_TOKEN

python -m cli.blaster status
python -m cli.blaster jobs
python -m cli.blaster mcp-info
python -m cli.blaster ugc-plan brief.json
```

See [`docs/AGENT_INTERFACES.md`](docs/AGENT_INTERFACES.md) for the complete interface and walk-test contract.

## Budget and approval safety

Provider spend is not authorized by a browser field or an agent prompt.

The backend uses a server-owned Redis wallet to atomically reserve:

1. the remaining generation allowance; and
2. the remaining provider-cost budget.

If either allowance is insufficient, generation is blocked before the media provider is called. The wallet state is mirrored to Supabase for durable reporting.

Paid generation additionally requires explicit approval. Publishing and paid-media activation have their own approval boundaries. Never move those controls into client JavaScript or an agent-only convention.

## Optional integrations

Integrations are client-scoped and disabled until configured.

| Integration | Role | Core dependency? |
|---|---|---|
| Fal.ai | media generation | configured production media provider |
| Self-hosted Supabase | canonical ledger/assets | yes in production |
| Shopify | orders/refunds/attribution | no |
| Meta Ads | experiment delivery/metrics | no |
| TikTok Ads | experiment delivery/metrics | no |
| Buffer | downstream social scheduling/publishing | no |

The Buffer adapter uses Buffer's GraphQL API and is enabled only with `PUBLISHING_PROVIDER=buffer` plus a server-side `BUFFER_API_KEY`. It does not bypass Buffer Blaster's human approval gate.

## Production architecture

The verified sovereign shape is:

```text
public frontend
      │
      ▼
FastAPI / Buffer Blaster API
      ├── Redis (sessions, queues, generation wallet)
      ├── money-loop worker
      └── supabase-kong
              │
              ▼
       self-hosted Postgres
       schema: buffer_blaster
```

Read [`docs/PRODUCTION.md`](docs/PRODUCTION.md) before deployment or rollback work.

## Repository map

```text
AGENTS.md           small agent router
CONTEXT.md          root ICM context
frontend/           Next.js public site + Studio
api/                FastAPI canonical backend
cli/                scriptable API client
supabase/           migrations + RLS boundary
skills/             stable creative/quality procedures
content/            editorial content
ops/                release/gauntlet/rollback evidence
docs/               product, interface and production references
tests/              executable system truth
```

Every major working area has a small `CONTEXT.md`. A cold agent should pass [`docs/ICM_WALK_TEST.md`](docs/ICM_WALK_TEST.md) without repository-wide archaeology.

## Read these first

For an AI agent:

1. [`AGENTS.md`](AGENTS.md)
2. [`CONTEXT.md`](CONTEXT.md)
3. the relevant area `CONTEXT.md`

For a human operator:

1. [`docs/POSITIONING.md`](docs/POSITIONING.md)
2. [`docs/AGENT_INTERFACES.md`](docs/AGENT_INTERFACES.md)
3. [`docs/PRODUCTION.md`](docs/PRODUCTION.md)
4. [`docs/APP_BOUNDARIES.md`](docs/APP_BOUNDARIES.md)
5. [`GATES.production.md`](GATES.production.md)

## Security rules

- Never commit provider tokens, service-role keys, operator tokens, or client credentials.
- Production secrets live in runtime environment stores/files only.
- No provider secret may use a `NEXT_PUBLIC_*` name.
- Keep workspace/client isolation enforced in the data layer.
- Do not claim a provider is live until its real account identity/readback contract has passed.
- Do not fabricate revenue, provider state, campaign state, or agent state.
- Publishing and paid actions remain human-controlled at the consequential transition.

## Product boundary

Buffer Blaster owns the creative system. External schedulers, social networks, stores, and ad networks remain separate systems connected through explicit adapters. This keeps the product useful even when one downstream integration is absent or replaced.

## License

Proprietary. All rights reserved.
