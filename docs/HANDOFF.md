# HANDOFF — Buffer Blaster

> Current zero-context handoff. Governance precedence remains
> `EMERALD_TABLETS.md` → `AGENTS.md` → accepted OpenSpec → ICM stage evidence.

## What this application is

Buffer Blaster is a standalone content/UGC operations application with a
Next.js frontend, FastAPI backend, canonical Supabase ledger, optional Rust hot
path, provider-neutral media generation, approval-gated publishing, and a
proof-first money-loop experiment layer.

## Current runtime shape

- `frontend/` — product UI, public site, Studio and admin surfaces.
- `api/` — auth, Studio, voice, MCP, media, billing, money loop and webhooks.
- `supabase/` — canonical `buffer_blaster` production schema and migrations.
- `scripts/selfhost/` — the only production backend/Vercel configuration path.
- `icm/` — human-editable campaign/experiment state machine.
- `ops/rollback/` — reversible release evidence.

The canonical production shape is Vercel for the frontend plus the self-hosted
FastAPI/worker stack behind Caddy/HTTPS. Existing historical `/opt/stavarai`
installation paths may remain for compatibility; they are not the product name
or a second architecture.

## Security truth

- There is no committed/default production password.
- The self-host installer generates app-owned operator/API credentials locally
  when blank.
- Provider/API/service-role credentials stay server-side.
- Service-role Supabase queries bypass RLS and must explicitly scope to
  `BUFFER_BLASTER_WORKSPACE_ID`.
- Public publishing and paid-media mutation require human approval.
- Configured integration state is not equivalent to verified connectivity.

## Proof-first money loop

Current ownership contract:

`SCAN -> QUALIFY -> MODEL -> PROVE -> JUDGE -> APPROVE -> TEST -> VERIFY -> CLOSE -> SCALE -> COMPOUND`

- Hermes/business orchestration: SCAN, QUALIFY, MODEL, CLOSE, COMPOUND.
- Buffer Blaster: PROVE, JUDGE, TEST, VERIFY, SCALE.
- Human gate: APPROVE, spend, publish, contractual commitment.

Implemented:

- persistent experiment/variant/attribution ledger;
- deterministic PASS / HOLD / ITERATE / KILL evaluator;
- Shopify signed webhook attribution;
- Meta/TikTok provider adapters and metric ingestion;
- hourly self-hosted money-loop worker;
- machine-readable Hermes handoff contract.

Important limitation: Meta and TikTok currently create **paused campaign
containers only**. They do not yet create the full creative + ad-set/ad-group +
ad delivery hierarchy, so `delivery_ready=false` until that follow-up is built
and verified against authorized provider accounts.

Shopify paid-order attribution works, but precise negative/partial refund
adjustments remain a follow-up before net-ROAS claims.

## Production activation sequence

1. Apply current Supabase migrations to the intended production project.
2. Configure VPS secrets privately from `.env.production.example`.
3. Run `scripts/selfhost/preflight.sh`.
4. Bring up/restart the API and `money-loop-worker` through the canonical compose
   path.
5. Configure Vercel with `scripts/selfhost/configure-vercel.sh` so live mode is
   false for demo/public-console flags and the API URL is HTTPS.
6. Register/verify Shopify webhook delivery.
7. Verify Meta/TikTok read-only account access.
8. Run `scripts/selfhost/smoke.sh`.
9. Only after the full paid-media delivery hierarchy exists, run the smallest
   capped human-approved provider proof.

## Current release gate

Every material PR must pass repository CI and the pinned OpenCodeReview Vibe
review gate. If OpenCodeReview fails because its external model backend is
unavailable, record that as review-infrastructure failure rather than a clean
review or a code failure.

For the latest wiring findings and remaining blockers, read
`docs/audits/2026-08-31-full-stack-wiring.md`.
