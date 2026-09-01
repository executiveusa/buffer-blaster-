# SECRETS.md — Runtime Secret Contract
# ICM Stage: 00_context | NEVER commit real values

## Canonical rule

Secrets are runtime configuration, not repository content. Do not put real
passwords, tokens, service-role keys, provider credentials, or webhook secrets
in source, docs, frontend variables, logs, issue comments, or CI output.

## Where secrets live

- Local development: `.env` or equivalent local environment file (gitignored).
- Self-hosted production: the install's `.env.production` file with mode `600`,
  or an external secret manager mounted into the runtime.
- Vercel: only variables actually required by Vercel-hosted code. Provider and
  backend credentials stay server-side and must never use a `NEXT_PUBLIC_*` name.
- Runtime-editable UI settings are **not a secret store**. The current Redis
  runtime store accepts only non-secret operator settings such as
  `ACTIVE_LLM_PROVIDER` and `AGENT_MAX_CHILDREN`.

## Core operator/security variables

```text
PLATFORM_NAME=Buffer Blaster
MASTER_ENCRYPTION_KEY=
DEMO_PASSWORD=
BLASTER_API_KEY=
TRIAL_SESSION_SECRET=
REDIS_PASSWORD=
REDIS_URL=
```

`DEMO_PASSWORD` is a historical variable name for the live operator password.
There is no committed default or fallback value. `scripts/selfhost/install.sh`
generates app-owned credentials locally when these core values are blank.

## Canonical production ledger

```text
BUFFER_BLASTER_WORKSPACE_ID=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_PROJECT_REF=
BUFFER_BLASTER_ASSET_BUCKET=buffer-blaster-assets
```

`SUPABASE_SERVICE_KEY` is backend-only. Service-role access bypasses RLS, so
application queries must still enforce `BUFFER_BLASTER_WORKSPACE_ID` explicitly.

Frontend-safe Supabase variables, if a public read-only surface genuinely needs
them, are separate:

```text
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Never expose the service-role key through a `NEXT_PUBLIC_*` variable.

## LLM providers

```text
ACTIVE_LLM_PROVIDER=openai
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
OPENAI_API_KEY=
OPENAI_MODEL=
GOOGLE_AI_API_KEY=
GOOGLE_MODEL=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
```

Provider/model selection remains environment-driven.

## Media generation

```text
FAL_KEY=
FAL_QUEUE_URL=https://queue.fal.run
FAL_TEXT_VIDEO_MODEL=
FAL_IMAGE_VIDEO_MODEL=
```

Credential-bearing Fal requests are restricted to the configured Fal queue
origin. Asset downloads use the separate media-download boundary.

## Proof-first money loop

```text
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
META_GRAPH_API_VERSION=
TIKTOK_ACCESS_TOKEN=
TIKTOK_ADVERTISER_ID=
TIKTOK_API_BASE_URL=
SHOPIFY_WEBHOOK_SECRET=
SHOPIFY_SHOP_DOMAIN=
SHOPIFY_ADMIN_ACCESS_TOKEN=
SHOPIFY_ADMIN_API_VERSION=
```

These values belong on the backend/VPS. A configured provider is not the same as
a verified provider; production readiness requires a successful read-only
handshake before any human-approved mutation.

## Stripe / commerce

```text
STRIPE_SECRET_KEY=
STRIPE_TRIAL_7_PRICE_ID=
STRIPE_TRIAL_30_PRICE_ID=
STRIPE_STARTER_PRICE_ID=
STRIPE_PRO_PRICE_ID=
```

Keep secret keys server-side. Public checkout references may be exposed only
through the intended application contract.

## Optional integrations

```text
HIGGSFIELD_API_KEY=
BUFFER_ACCESS_TOKEN=
APIFY_API_TOKEN=
FIRECRAWL_API_KEY=
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
TELEGRAM_BOT_TOKEN=
TELEGRAM_USER_ID=
VISIONCLAW_WEBHOOK_SECRET=
EMAIL_API_KEY=
GITHUB_TOKEN=
```

## Deployment

The only supported production deployment paths are:

- Backend/VPS: `scripts/selfhost/install.sh`
- Frontend/Vercel: `scripts/selfhost/configure-vercel.sh`

Legacy deploy entrypoints delegate to those scripts. They must never discover
credentials by scanning unrelated filesystem locations or inject a known
password into an environment.
