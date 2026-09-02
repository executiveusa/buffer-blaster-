# Production

## Current verified baseline
The last production-verified `main` before this positioning pass is:

`06529027133c68640606418682382f14ff59a78f`

Do not describe this branch as production until it is reviewed, merged, deployed, and smoke-tested.

## Topology
- Public frontend: Vercel deployment currently reached at `https://stavarai-platform.vercel.app`
- Backend/API: self-hosted FastAPI on the sovereign VPS
- Public API health: `https://stavarai.31.220.58.212.sslip.io/api/health`
- Database: self-hosted Supabase/Postgres, schema `buffer_blaster`
- Worker: long-running money-loop worker on the VPS
- Redis: server-side session, queue, and generation-wallet enforcement

The historical `/opt/stavarai` install path and `stavarai-*` container names are compatibility details only. Public product identity is Buffer Blaster.

## Release proof
Before a new production claim:
1. full repository CI is green, except an explicitly documented external CI outage;
2. no secret values appear in source, logs, screenshots, or browser bundles;
3. `scripts/selfhost/preflight.sh` passes on the target host;
4. `scripts/selfhost/smoke.sh` passes;
5. public `/api/health` reports `platform: buffer blaster`;
6. self-hosted Supabase connectivity works from inside the API container;
7. MCP/CLI walk test passes using legitimate operator authentication;
8. paid/publish paths still reject unapproved actions;
9. mobile/browser screenshots are reviewed at required breakpoints;
10. rollback SHA is recorded.

## Optional providers
Fal.ai and self-hosted Supabase are part of the verified core environment. Meta, TikTok, Shopify, and Buffer publishing are account-scoped optional integrations. Do not mark any of them live-verified until their own auth/account/readback contract passes with real credentials.

## Rollback
Deployments must retain the last verified `main` SHA. If a new release fails health, smoke, interface, security, or browser gates, restore the previous verified SHA and recreate only the Buffer Blaster containers. Do not alter the shared Supabase stack to hide an application failure.
