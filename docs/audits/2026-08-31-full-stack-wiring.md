# Full-Stack Wiring Audit — 2026-08-31

## Scope

Target: `executiveusa/buffer-blaster-` at baseline main
`cfcbf1efbe25234c84fc166d860bd9e45424f95e`.

Audit inputs:

- operator-provided `full-stack-wiring-audit-v2.0.0(3).zip`;
- the audit contract already imported into this repository as
  `openspec/changes/wiring-truth-pricing-v2/`;
- current Buffer Blaster runtime, frontend, migrations, deployment scripts,
  provider adapters, tests, and ICM contracts;
- `executiveusa/open-code-review` as the independent PR review gate.

The goal is wiring truth: every user-visible claim and every integration path
must correspond to a real, authorized, observable runtime path. Configured is
not verified; queued is not complete; a provider campaign container is not a
live delivered ad.

## Severity summary

| Severity | Finding | State in this repair |
| --- | --- | --- |
| Critical | Competing legacy deploy paths could force demo mode in production, inject a known password, use HTTP direct-IP API wiring, and deploy to obsolete identities | Fixed |
| Critical | Legacy full deploy script searched unrelated filesystem locations for a Supabase service-role key and copied it into app config | Fixed by retiring/delegating legacy path |
| High | Service-role money-loop reads/updates were not consistently workspace-scoped even though service-role bypasses RLS | Fixed |
| High | Stale highest-priority governance still described a committed/well-known backend password and contradicted current product/auth truth | Fixed |
| High | Agent-readable deployment/handoff docs could recreate the obsolete insecure topology | Fixed by archival routing stubs |
| High | Meta/TikTok adapters create only campaign containers, not the complete creative/ad-set/ad delivery hierarchy | OPEN release blocker |
| Medium | Shopify webhook could accept an event with no durable idempotency identifier | Fixed |
| Medium | Shopify cancellation/refund events do not yet produce precise negative/net-revenue adjustments | OPEN measurement blocker |
| Medium | Buffer Blaster PR review was pinned to an older OpenCodeReview Vibe workflow revision | Fixed; pinned to current reviewed revision |
| External | OpenCodeReview's current reusable workflow depends on GitHub Models, which previously returned retirement/brownout errors | Must be verified by this PR run |

## Repairs made

### 1. One production deployment path

Canonical paths are now:

- backend/VPS: `scripts/selfhost/install.sh`;
- frontend/Vercel: `scripts/selfhost/configure-vercel.sh`.

Legacy entrypoints remain as compatibility wrappers only. They may not carry a
second environment contract.

The canonical Vercel helper now targets Buffer Blaster, forces live mode, keeps
the public console off, and uses an HTTPS API domain. The canonical self-host
installer generates app-owned credentials locally when blank and no longer
silently binds a fresh install to a committed Supabase project ref.

### 2. Auth/secret contract truth

`EMERALD_TABLETS.md`, `.env.example`, and `docs/SECRETS.md` now agree with the
live auth code:

- no committed/default production password;
- `DEMO_PASSWORD` is a historical variable name, not a demo-grade security
  exception in production;
- backend/API/provider credentials stay server-side;
- runtime UI settings are non-secret Redis values only;
- agent-readable legacy handoffs cannot instruct secret scavenging.

### 3. Workspace isolation under service-role access

`api/services/money_loop.py` and
`api/services/performance_ingestion.py` now apply
`workspace_id=eq.<BUFFER_BLASTER_WORKSPACE_ID>` to service-role reads and
updates. Parent resources are validated inside the configured workspace before
money-loop writes are accepted.

This is required even with RLS enabled because the service-role key bypasses
RLS by design.

### 4. Shopify webhook idempotency

The webhook now rejects deliveries for which no Shopify event ID, webhook ID,
or payload ID is available. This prevents unrelated id-less deliveries from
colliding under the attribution ledger's unique `(source, external_event_id)`
constraint.

### 5. OpenCodeReview reproducibility

`.github/workflows/vibe-code-review.yml` is pinned to
`executiveusa/open-code-review` commit
`c8e4c02b6f0e9467b755fc7e24b2619f6854a6a4` rather than an older workflow
revision or a floating ref.

The PR generated from this branch is the execution proof for OpenCodeReview.
If the workflow fails because GitHub Models is unavailable/retired, that is an
external review-infrastructure failure and must not be reported as a clean code
review.

## Open release blockers

### A. Paid-media launch is not end-to-end

Current Meta and TikTok adapters can create/pause/read a campaign container and
read metrics. They do **not** yet create and bind the complete delivery objects
needed to put a Buffer Blaster creative into a live test.

Required follow-up for each provider:

1. verified account/ad-account authorization;
2. creative upload/binding;
3. ad-set/ad-group creation with bounded audience/budget/schedule;
4. ad creation pointing at the correct creative and tracking link;
5. durable external IDs for every layer;
6. paused-by-default creation;
7. explicit human approval immediately before activation/spend;
8. read-back verification that the expected creative is attached;
9. pause/rollback verification;
10. provider sandbox or smallest capped live proof.

Until that exists, Buffer Blaster may say **campaign container created**, not
**ad launched** or **paid experiment live**.

### B. Refund/net-revenue accounting is incomplete

`orders/paid` revenue is attributed. Cancellation/refund events currently do not
calculate precise negative revenue adjustments, so deterministic ROAS is gross
paid-order revenue, not guaranteed net revenue after refunds.

Before net-ROAS claims are allowed, implement a durable adjustment model with
Shopify refund identifiers, partial-refund amounts, deduplication, and tests.

### C. Live provider verification is still required

No audit or CI job should spend money. Before first paid proof, production must
show successful read-only handshakes for Meta, TikTok, Shopify webhook delivery,
Supabase ledger access, and the deployed worker.

## Merge gates

This repair is mergeable only when:

- Python tests pass;
- frontend structural gauntlet/lint/build/route smoke pass;
- fresh PostgreSQL migration proof passes;
- production Docker/compose smoke passes;
- no material unresolved review finding remains;
- OpenCodeReview either completes or its failure is proven to be external to
  the code and another independent review signal is available;
- no production deploy/provider spend was required to obtain the evidence.

## Rollback

See `ops/rollback/full-stack-wiring-audit-2026-08-31.json`.

This repair contains no database migration, production deployment, or provider
mutation. Reverting the squash merge restores the prior application state.
