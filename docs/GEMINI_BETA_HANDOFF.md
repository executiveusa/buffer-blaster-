# Gemini Beta Production Handoff

This is the zero-context handoff for taking Buffer Blaster / Stavarai Social Studio from the merged beta codebase to a live, credentialed beta.

## Mission

Stand up the private FastAPI backend on a Linux VPS, keep the Next.js frontend on the canonical Vercel project, connect Supabase + OpenAI + Fal, and prove one complete UGC-to-publish loop without weakening the human approval boundary.

Canonical assets:

- GitHub: `executiveusa/buffer-blaster-`
- Vercel project: `stavarai-platform` (`prj_n6CJYyzdUmqHNJ8qlSJalVGerUUW`)
- Vercel team: `team_2MkWeFBaSCv7DOvEy0OlX4s3`
- Frontend: `https://stavarai-platform.vercel.app/studio`
- Supabase project/ref: `cyxdevcjycmffhmwxojh`
- Supabase URL: `https://cyxdevcjycmffhmwxojh.supabase.co`

Do not use the stale Vercel project named `buffer-blaster`; the canonical frontend project is `stavarai-platform` and its root directory is `frontend`.

## Non-negotiable production boundary

No public social action may occur until the operator has reviewed the exact content/media and explicitly approved it. Do not add an alternate publisher route, background auto-approve, fake account ID, or demo receipt disguised as a real receipt.

## 1. DNS and host

Provision an Ubuntu/Debian VPS with Docker-capable resources. For initial beta, start with at least 4 vCPU / 8 GB RAM and increase after observed load. Point an API hostname such as `api.example.com` at the VPS before the installer runs so Caddy can obtain TLS.

The media generation workload is offloaded to Fal and the primary database is Supabase, so the API VPS is mostly orchestration, HTTP and agent traffic.

## 2. One-click backend install

Run on the VPS:

```bash
curl -fsSL https://raw.githubusercontent.com/executiveusa/buffer-blaster-/main/scripts/selfhost/install.sh \
  | sudo bash -s -- --domain api.example.com
```

The installer:

- installs Docker when absent;
- checks out the canonical repo into `/opt/stavarai`;
- creates `/opt/stavarai/.env.production`;
- generates `MASTER_ENCRYPTION_KEY`, `BLASTER_API_KEY`, and `DEMO_PASSWORD` locally when blank;
- starts FastAPI behind Caddy with automatic HTTPS;
- does not print generated secrets;
- runs a non-paid preflight.

It intentionally does not invent third-party credentials.

## 3. Secret placement

### VPS only — `/opt/stavarai/.env.production`

Required for a fully working beta:

```text
MASTER_ENCRYPTION_KEY
DEMO_PASSWORD
BLASTER_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_KEY
SUPABASE_PROJECT_REF
OPENAI_API_KEY
OPENAI_MODEL
FAL_KEY
FAL_TEXT_VIDEO_MODEL
FAL_IMAGE_VIDEO_MODEL
ALLOWED_ORIGINS
```

Optional only when the feature is enabled:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_USER_ID
VISIONCLAW_WEBHOOK_SECRET
STRIPE_SECRET_KEY
STRIPE_FOUNDING_PAYMENT_LINK
STRIPE_FOUNDING_PRICE_ID
EMAIL_API_KEY
APIFY_API_TOKEN
FIRECRAWL_API_KEY
AIRTABLE_API_KEY
AIRTABLE_BASE_ID
```

Never put `BLASTER_API_KEY`, `OPENAI_API_KEY`, `FAL_KEY`, `SUPABASE_SERVICE_KEY` into any `NEXT_PUBLIC_*` variable or GitHub file.

After editing server secrets:

```bash
cd /opt/stavarai
chmod 600 .env.production
docker compose -f docker-compose.prod.yml up -d --build
bash scripts/selfhost/preflight.sh
bash scripts/selfhost/smoke.sh
```

## 4. OpenAI

Use a project-scoped OpenAI API key. `ACTIVE_LLM_PROVIDER=openai`; keep `OPENAI_MODEL` environment-driven. Do not hardcode the model in application source.

## 5. Fal UGC

The live Fal catalog was checked during this packaging slice. Current quality-first beta candidates are:

```text
FAL_TEXT_VIDEO_MODEL=minimax/h3-max/text-to-video
FAL_IMAGE_VIDEO_MODEL=minimax/h3-max/image-to-video
```

The provider reported pricing as `$0.00017 / compute second` for each H3 Max endpoint at the time of the check. Recheck pricing before changing customer credit economics.

For a faster alternative, evaluate the current Hailuo 2.3 Fast endpoints. Keep all endpoint IDs in environment variables so the studio can switch providers/models without code changes.

Do not use a paid generation as a health check. The first paid render belongs in the explicit end-to-end beta proof.

## 6. TryPost publishing kernel

Keep TryPost as a separate AGPL service; do not merge its source tree into this proprietary repo.

Upstream production compose currently includes PostgreSQL 16, Redis, queue workers/scheduler behavior, Reverb WebSockets and optional Caddy. Use the official `compose.prod.yaml` from `trypostit/trypost`.

For a durable production deployment, Gemini must set:

- `APP_KEY`;
- a strong Postgres password;
- a strong Reverb secret;
- persistent `PASSPORT_PRIVATE_KEY` and `PASSPORT_PUBLIC_KEY` so API/MCP tokens survive container recreation;
- `APP_URL=https://<try-post-domain>`;
- social provider OAuth credentials for every network enabled.

Important: the upstream published image currently bakes the Reverb client for localhost. For a custom production hostname, rebuild the TryPost image with the upstream-documented build arguments:

```text
VITE_REVERB_HOST=<try-post-domain>
VITE_REVERB_PORT=443
VITE_REVERB_SCHEME=https
```

Then expose it behind TLS and create the TryPost API token used by Buffer Blaster as `TRYPOST_API_KEY`.

Minimum verification before wiring Buffer Blaster:

1. TryPost web UI loads on HTTPS.
2. At least one real social account is connected.
3. Its account endpoint returns the real active UUID.
4. API token survives a TryPost container restart.
5. No post is sent yet.

## 7. Vercel live-mode switch

The browser uses the normal operator session token; do not inject `BLASTER_API_KEY` into the frontend.

On an operator machine with a Vercel token:

```bash
cd /opt/stavarai
VERCEL_TOKEN='<private token>' \
  bash scripts/selfhost/configure-vercel.sh --domain api.example.com
```

This sets/updates only:

```text
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_PUBLIC_CONSOLE=false
NEXT_PUBLIC_API_URL=https://api.example.com
SITE_URL=https://stavarai-platform.vercel.app
```

and triggers a new production deployment. Vercel environment changes do not affect an already-built deployment until a new deployment is created.

If a Vercel-hosted server route needs Stripe later, add `STRIPE_SECRET_KEY` as a server-only Vercel production variable, never a `NEXT_PUBLIC_*` variable.

## 8. Supabase

Use project `cyxdevcjycmffhmwxojh`. The `buffer_blaster` schema already contains the campaign, creative job, content, approval, channel, publish-job and publish-receipt state required by the beta flow.

The one-click beta slice adds only FK-covering indexes for the hot campaign -> creative -> approval -> publish -> receipt joins. It does not rewrite RLS or touch unrelated schemas in the shared project.

Before beta users enter:

- confirm the migration `buffer_blaster_beta_scale` is applied;
- run Supabase security + performance advisors;
- do not modify unrelated schemas because the project contains other workloads.

## 9. Capacity model

Initial API defaults:

```text
WEB_CONCURRENCY=4
UVICORN_LIMIT_CONCURRENCY=1000
UVICORN_BACKLOG=2048
MAX_REQUEST_BYTES=2000000
```

Tune worker count to available CPU/RAM after load testing; do not blindly multiply workers. Caddy terminates TLS and keeps the API container off the public host port. Docker restarts unhealthy/rebooted services. Logs are rotated.

Scale components independently:

- Vercel: frontend/CDN and Next.js routes;
- API VPS: orchestration and authenticated commands;
- Fal: asynchronous media-generation queue;
- Supabase: persistent application state/realtime;
- TryPost: its own Postgres/Redis/publishing workers.

Before inviting larger cohorts, run load tests against read/status and command preparation routes. Do not load-test paid Fal generation or real publishing endpoints.

## 10. Required beta proof

Do not mark the system fully working until this exact chain has real receipts:

```text
real product/reference image
  -> real Fal UGC render
  -> operator reviews exact rendered asset + copy
  -> explicit approval
  -> resolve a real active TryPost social account UUID
  -> schedule through Buffer Blaster
  -> TryPost publishes
  -> capture external post ID / publish receipt
  -> performance event returns to the system
```

Start with one controlled test account/post. The publishing boundary must remain fail-closed when `approved=false`.

## 11. Rollback

Application rollback:

```bash
cd /opt/stavarai
git fetch origin
git checkout <previous-known-good-sha>
docker compose -f docker-compose.prod.yml up -d --build
```

Frontend rollback: restore the prior Vercel production deployment or return `NEXT_PUBLIC_DEMO_MODE=true`, redeploy, and keep the VPS online for diagnosis.

Database rollback: only the indexes introduced by `buffer_blaster_beta_scale` may be dropped. Never rollback by deleting tables, schemas, content, approvals or receipts.

## Definition of beta-ready

Beta-ready means all of the following are proven, not assumed:

- GitHub CI green on the deployed SHA;
- VPS `/api/health` green over HTTPS;
- authenticated `/api/studio/status` green;
- OpenAI configured;
- Fal configured and one real render completed;
- TryPost configured and one real account resolved;
- explicit approval gate tested both blocked and allowed;
- Vercel live mode points to the VPS;
- one real scheduled/published test returns an external receipt;
- Vercel and VPS show no critical runtime errors during the proof window.
