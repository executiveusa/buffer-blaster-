# Agent Context — Buffer Blaster / Social Studio

## Repo Purpose
Agent-first content operations and UGC creation studio for brands, agencies, and creators. Handles campaign planning, UGC prompt compilation, media generation, quality scoring, human approval gates, and multi-channel scheduling.

## Current Stack & Architecture
- **Frontend**: Next.js 16 (Turbopack) + Tailwind CSS on Vercel (`stavarai-platform`, Project ID: `prj_n6CJYyzdUmqHNJ8qlSJalVGerUUW`, URL: `https://stavarai-platform.vercel.app/studio`)
- **Backend**: FastAPI on Ubuntu VPS `31.220.58.212` (`https://stavarai.31.220.58.212.sslip.io`) with 4 Uvicorn workers (`WEB_CONCURRENCY=4`), reverse-proxied via Host Caddy with auto Let's Encrypt TLS.
- **Cache & Sessions**: Dedicated Redis (`stavarai-redis-1`, `redis:6379/0`) for multi-worker session sharing and task queue persistence.
- **Data Scope**: Supabase (`https://cyxdevcjycmffhmwxojh.supabase.co`).
- **Media Engine**: Fal.ai (`minimax/h3-max` text/image-to-video).
- **Publishing Boundary**: Fully decoupled standalone architecture (`DisabledPublishingProvider` default; zero TryPost runtime dependencies).

## Canonical Baseline
- **GitHub Repository**: `https://github.com/executiveusa/buffer-blaster-.git`
- **Canonical Main Branch**: `main`
- **Canonical SHA**: `6efba1e2256cb4ab46005222be6ca1121a2c9fcb` (PR #28 merged)

## Verified Pipeline Status
- **Core Health**: `status: ok`, `approval_gate: true`, `publishing: {enabled: false, required_for_core: false}`
- **Deterministic Pipeline**: Tested and operational (`/api/studio/campaigns/plan`, `/api/studio/ugc/prompt`).
- **Test Run (Cella Coffee)**: Generated 7-day campaign brief, daily angles, hooks, copy, CTAs, and universal 9:16 video prompt.
- **Provider Status**:
  - Redis: Working (PING pass, SET/GET pass, shared sessions pass)
  - Fal: Key set & authenticated; account locked due to exhausted balance on fal.ai
  - OpenAI: Key set; HTTP 429 quota exhausted
  - Supabase: URL set; `SUPABASE_SERVICE_KEY` pending private entry

## Immediate Next Recommendations
1. Top up Fal account balance or supply active FAL key in Infisical.
2. Provide `SUPABASE_SERVICE_KEY` in `.env.production` for persistent Postgres storage.
3. Top up OpenAI quota.
4. Execute the approved Cella Coffee single test render.
5. Onboard first 3–5 beta users.
