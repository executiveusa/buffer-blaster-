# Buffer Blaster — Production Playwright Audit

Date: 2026-09-22  
Production URL: https://bufferblaster.netlify.app  
Canonical Netlify project: `bufferblaster`  
Production recovery deploy: `6ab29fd80566590008c70a76`  
Production recovery commit: `09bdc4fd50f172f36eb250d0ee5c700d1a2f7501`  
Repair / browser-audit PR: #92  
Method: real Chromium through Playwright, direct runtime probes, source-level control scan, and a safe local private-UI pass. Paid generation, publishing, ad activation, destructive actions, and credential bypasses were not authorized or executed.

## Release decision

**PUBLIC SITE: PASS. PRIVATE LIVE STUDIO: HOLD.**

The production 404 has been repaired and the canonical public site is live again with a real Netlify Next.js Server Handler. Public navigation, media, install inquiry, mobile layout, anonymous auth boundary, robots, and sitemap were exercised successfully.

The remaining primary production blocker is browser CORS between `https://bufferblaster.netlify.app` and the sovereign backend. The source repair exists on this branch, but the VPS backend must deploy it before a legitimate authenticated operator Playwright pass can succeed.

## Findings

### BB-PW-001 — RESOLVED P0 — production root returned 404

Original observation:
- `https://bufferblaster.netlify.app/` returned the Netlify 404 page.
- The broken deploy had no Next.js Server Handler.

Root cause:
- `netlify.toml` had been removed even though the connected Netlify project still needs the Next.js build/plugin configuration.

Production repair:
- restored `netlify.toml` directly on `main`;
- recovery commit: `09bdc4fd50f172f36eb250d0ee5c700d1a2f7501`;
- recovery deploy: `6ab29fd80566590008c70a76`;
- Netlify deployed `@netlify/plugin-nextjs@5.16.0` and one Next.js Server Handler.

Current proof:
- `/` 200
- `/install` 200
- `/pricing` resolves to `/install`
- `/robots.txt` 200
- `/sitemap.xml` 200

### BB-PW-002 — OPEN P1 — canonical frontend blocked by deployed backend CORS

Real production Playwright sign-in probe:
- browser attempted `POST https://stavarai.31.220.58.212.sslip.io/api/auth/verify`;
- Chromium blocked the request because the preflight response did not include `Access-Control-Allow-Origin: https://bufferblaster.netlify.app`;
- UI truthfully displayed `Failed to fetch`.

Direct preflight reproduced the problem.

Source repair on this branch:
- `api/app.py` includes `https://bufferblaster.netlify.app` in the canonical origin set.

Required acceptance:
1. deploy the branch CORS change to the VPS backend;
2. repeat OPTIONS preflight from the canonical origin;
3. sign in with an authorized operator credential;
4. verify `/api/auth/session` and Studio calls in Chromium.

### BB-PW-003 — OPEN P1 / SOURCE FIXED — model picker transport was structurally broken

Current production `GET /api/models` returns HTTP 502:
`Model list service could not be reached.`

The previous proxy required a server-side `BLASTER_API_KEY` in Netlify and duplicated the normal operator-auth path.

Repair on this branch:
- remove `frontend/src/app/api/models/route.ts`;
- load `/api/studio/providers/models` through the authenticated Studio API client;
- carry the returned server allowlist into the Create model selector;
- clear expired sessions and return to operator sign-in.

Acceptance:
- after the CORS/auth repair is deployed, sign in and verify the selector contains the exact backend-returned model IDs.

### BB-PW-004 — PASS — production public routes and auth boundary

Real Playwright verified:
- `/` 200
- `/install` 200
- `/pricing` → `/install`
- `/robots.txt` 200
- `/sitemap.xml` 200
- every anonymous `/studio/*` route lands on `/admin?next=...`
- protected admin pages return to `/admin` without a session.

### BB-PW-005 — PASS — homepage controls and media

Clicked in real production Chromium:
- Buffer Blaster home
- Proof
- How it works
- Ownership
- Models
- Request install
- Request a private install
- Watch real output
- Watch the proof
- Install
- Studio

Settled media inspection:
- Selva & Sea hero: readyState 4, no media error
- Selva & Sea proof: readyState 4, no media error
- Streetwear proof: readyState 4, no media error

Navigation-related `ERR_ABORTED` media/RSC requests during rapid click-through were page-transition cancellations; settled media passed.

### BB-PW-006 — PASS — install inquiry end-to-end

Real production Playwright:
- work-email input usable;
- submit enabled;
- `POST /api/install-inquiry` returned HTTP 200;
- UI displayed `Install request received.`.

QA record:
`buffer-blaster-playwright-live-qa-20260922@example.com`

This record was intentionally marked as QA. No cleanup endpoint was available in this pass, so do not claim it was deleted.

### BB-PW-007 — PASS — public mobile layout

Viewport: 390 × 844.

Verified:
- clientWidth 390
- scrollWidth 390
- no page-level horizontal overflow
- public CTA/footer controls visible
- videos present and loadable

### BB-PW-008 — PASS SOURCE / LOCAL UI — mobile private navigation

A user-perspective local private-UI pass found that the mobile Studio previously exposed only the top-level Create shortcut and no practical route to several Studio sections.

Repair on this branch:
- mobile Studio navigation now exposes:
  Overview, Create UGC, My ads, Moodboards, Canvas, Campaigns, Calendar, Analytics, Settings.
- mobile Admin navigation now exposes:
  Dashboard, Clients, Content, Blog, Analytics, Settings.

Playwright recheck:
- both nav bars visible at 390 × 844;
- no page-level horizontal overflow.

### BB-PW-009 — RESOLVED SOURCE DEFECT — Add Client was a dead button

The full control click-through found `/admin/clients` → `Add client` had no handler.

Repair on this branch:
- added an authenticated `createClient()` frontend API call;
- added a real New Client form with Name, Slug, Niche, Create, Cancel, and validation;
- production path POSTs to `/api/admin/clients`;
- demo path remains clearly simulated.

Playwright local verification:
- Add client opens form;
- valid fields can be entered;
- Create client produces a new demo client card;
- no console error.

No production client record was created during this audit.

### BB-PW-010 — PASS — source-wide dead-control / route scan

Static scan across `frontend/src/**/*.tsx` on the repaired branch found:
- dead non-submit buttons: **0**
- broken internal route links: **0**
- discovered app page routes: **23**

This is supplementary evidence; runtime Playwright remains the release authority.

### BB-PW-011 — PASS LOCAL UI — safe component click-through

A production build of the audit branch passed TypeScript and Next.js compilation.

A separate safe local private-UI run exercised the components without provider spend or production writes.

Examples clicked:
- Studio: Speak command, Run command
- Create: Build ad plan
- Moodboards: Choose image
- Campaigns: Instagram/Facebook/TikTok/YouTube toggles
- Campaign planning: Generate canonical campaign → rendered a 7-day simulated sequence
- Calendar: Resolve connected accounts
- Studio Settings: Refresh
- Admin Dashboard: Dismiss onboarding
- Admin Content: client toggles
- Admin Settings: tabs and provider Test controls
- Admin Clients: Add client → completed form flow

Guarded consequential controls were not bypassed.

### BB-PW-012 — OPEN P1 — legacy paid-pass contract remains in Create

Current Create still carries legacy language/state around:
- paid pass;
- Ad Credits;
- trial cookie / checkout activation;
- `Start with a paid test pass`;
- legacy package economics.

That conflicts with the current one-time private-install product contract.

The backend already has a server-owned wallet/allowance and optional internal-wallet provisioning. This should be reconciled end-to-end rather than cosmetically hiding the trial UI.

### BB-PW-013 — OPEN P2 DEV-TOOLING — dependency audit

Exact branch recheck:
- `npm audit --omit=dev`: **0 vulnerabilities**
- full `npm audit`: **1 high**, **0 critical**
- affected transitive package: `browserslist <=4.28.6`, pulled through the development lint/Babel toolchain
- production runtime dependency audit is clean in this pass

Advisories:
- GHSA-c83g-rgw3-j3cx
- GHSA-73wf-gq98-2v4g

This is development tooling rather than a shipped production dependency, but it should still be updated or explicitly accepted before the audit branch is considered fully clean.

### BB-PW-014 — SOURCE FIXED — obsolete public product surfaces

The expanded production route walk found two still-reachable historical surfaces:

- `/founding` advertised a **$29 Founding Creator** offer that conflicts with the current one-time private-install commercial contract.
- `/create` exposed the older local-first Creator Studio and browser-local library outside the governed private Studio.

Repair on this branch:
- `/founding` redirects to `/install`;
- `/create` redirects to `/studio/create`, which then applies normal operator authentication.

Local production-mode Playwright verification:
- `/founding` lands on `/install` and no $29 offer remains;
- `/create` lands on `/admin?next=%2Fstudio%2Fcreate` for an anonymous user.

### BB-PW-015 — SOURCE FIXED — RSS used placeholder host

Production `/blog/rss.xml` emitted `https://example.com` for channel and post URLs.

Repair on this branch:
- RSS now uses the shared canonical `SITE_URL`;
- the default `SITE_URL` fallback is `https://bufferblaster.netlify.app`, not the retired Stavarai/Vercel hostname.

Verification:
- all seven current blog post routes return 200 in the branch production build;
- RSS contains the canonical Buffer Blaster host and no `example.com` / retired Stavarai host.

## Backend runtime truth

Verified live:
`GET https://stavarai.31.220.58.212.sslip.io/api/health` → HTTP 200.

Reported runtime state:
- status: ok
- platform: buffer blaster
- media configured: true
- storage configured: true
- ledger backend: supabase
- ledger persistent: true
- ledger canonical: true
- publisher configured: false
- approval gate: true

Publishing is therefore **NOT CONFIGURED**, not proof of a broken core generation path.

## Playwright MCP installed in the repository

Project MCP config:
- `.mcp.json`
- official `@playwright/mcp@latest`
- Chromium
- headless
- isolated browser context

Future agent instructions:
- `AGENTS.md` requires Playwright browser verification for UI/auth/form/navigation/component/release work.
- `docs/PLAYWRIGHT_MCP.md` defines the safe production audit contract.

Deterministic suite:
- `frontend/playwright.config.ts`
- `frontend/e2e/production.spec.ts`
- `frontend/scripts/run-production-playwright.sh`
- `.github/workflows/playwright-production-audit.yml`

The suite preserves failure reports/traces/screenshots/video and separates:
- read-only/safe control testing;
- optional draft writes via `PLAYWRIGHT_ALLOW_DRAFT_WRITES=true`;
- optional form submission;
- authenticated operator testing;
- consequential paid/publish/destructive controls, which remain gated.

## Current release gate

Completed:
1. production Next.js runtime restored;
2. canonical public routes verified;
3. homepage navigation clicked;
4. public media verified;
5. install inquiry persisted successfully;
6. public mobile overflow checked;
7. anonymous Studio/admin access boundary verified;
8. source-wide dead-button/internal-link scan clean;
9. mobile Studio/Admin navigation repaired;
10. dead Add Client control repaired;
11. branch production build passes;
12. Playwright MCP and recurring browser suite added.

Remaining before a full **production-ready private Studio** claim:
1. deploy backend canonical CORS repair;
2. run authenticated production Playwright with an authorized operator credential;
3. verify real model selector contents against `/api/studio/providers/models`;
4. click every safe private Studio control against the real backend;
5. verify zero unexplained browser console/network failures;
6. reconcile installed-operator allowance UX vs legacy trial/pass UI;
7. update or explicitly accept the remaining dev-only Browserslist advisory;
8. deploy the retired-route/RSS/mobile/client-control repairs with the browser-audit branch;
9. keep paid generation and publishing behind explicit human approval.
