# Buffer Blaster — Production Playwright Audit

Date: 2026-09-22  
Production URL: https://bufferblaster.netlify.app  
Audited repair preview: https://deploy-preview-92--bufferblaster.netlify.app  
Repair PR: #92  
Method: real headless Chromium through Playwright + direct runtime checks. High-risk paid/publish/destructive controls were not bypassed.

## Release decision

**HOLD production merge until the P0/P1 items below are cleared.**

The current production hostname returns Netlify 404. The repair preview restores the Next.js runtime and passes the public user journey. The sovereign backend health endpoint is green, but authenticated Studio traffic still requires the canonical frontend origin to be deployed in backend CORS before a real operator browser pass can succeed.

## Findings

### BB-PW-001 — P0 — production root is 404

Observed:
- `https://bufferblaster.netlify.app/` returns HTTP 404 and title `Page not found`.
- The same was reproduced with Playwright and curl.

Root cause:
- commit `83cd0be157c767986ad1171b98e2b028bd31fd9b` removed `netlify.toml` as a "dead" artifact.
- The connected Netlify project still requires that file to build/deploy the Next.js runtime correctly.
- The broken production deploy showed no Next.js server function.

Repair on this branch:
- restore the known Netlify Next.js configuration in `netlify.toml`.
- preview now deploys the Netlify Next.js Server Handler and returns HTTP 200.

Acceptance:
- production root, /install, /pricing, robots, sitemap and Studio auth boundary return expected responses after merge/deploy.

### BB-PW-002 — P1 — production frontend is not accepted by backend CORS

Observed preflight:
- Origin `https://bufferblaster.netlify.app` did not receive `Access-Control-Allow-Origin`.
- Browser sign-in from the deploy preview correctly exposed the same CORS failure for the preview origin.

Repair on this branch:
- add `https://bufferblaster.netlify.app` to the backend canonical origin set in `api/app.py`.

Important:
- deploy previews are intentionally not granted authenticated Studio CORS access. Logging an operator into arbitrary PR preview code would widen the secret/session blast radius.
- authenticated end-to-end proof must therefore be run against the final canonical production origin after the backend CORS fix is deployed.

### BB-PW-003 — P1 — model picker backend call was structurally broken

Observed:
- previous `GET /api/models` returned HTTP 502: `Model list service could not be reached.`
- canonical Netlify has backend URL variables but no `BLASTER_API_KEY`.
- the proxy called `backendHeaders()`, which requires that server secret.

Repair on this branch:
- remove the redundant `/api/models` secret-bearing proxy.
- load `/api/studio/providers/models` through the same authenticated browser/operator API used by the rest of Studio.
- expired operator sessions now clear and return to sign-in.

Acceptance:
- after canonical production CORS is deployed and operator auth succeeds, the Model select must list the server-returned allowlisted model IDs.

### BB-PW-004 — PASS — public repair-preview routes

Real Playwright verified:
- `/` 200
- `/install` 200
- `/pricing` resolves to `/install`
- `/robots.txt` 200
- `/sitemap.xml` 200
- every anonymous `/studio/*` route redirects to `/admin?next=...`
- `/admin/settings` redirects anonymous users to `/admin`

No page errors or console errors occurred on those public route loads.

### BB-PW-005 — PASS — homepage controls and media

Clicked and verified:
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
- Buffer Blaster home link

Media:
- Selva & Sea hero video: readyState 4, no media error.
- Selva & Sea proof video: readyState 4, no media error.
- Streetwear proof video: readyState 4, no media error.

Request aborts observed during rapid page-to-page audit were navigation cancellation of media loads, not media HTTP failures; direct settled video inspection loaded all three.

### BB-PW-006 — PASS — install inquiry end-to-end

Real Playwright:
- work-email field accepts a valid email.
- submit is enabled.
- submitted an explicitly marked QA record.
- `POST /api/install-inquiry` returned HTTP 200.
- UI reached `Install request received.`

QA address used:
`buffer-blaster-playwright-production-qa-20260922-b@example.com`

### BB-PW-007 — PASS — mobile public shell

Viewport: 390×844.

Observed:
- document clientWidth = 390
- document scrollWidth = 390
- no page-level horizontal overflow
- public CTA/footer links remain visible
- no console errors on homepage.

### BB-PW-008 — BLOCKED BY AUTH/CORS — private Studio component click-through

Anonymous behavior is correct: Studio routes redirect to operator sign-in.

A deliberately wrong-password test:
- enabled Sign in after password entry.
- browser request reached the backend boundary but was blocked by CORS on the preview origin.
- no credential guessing or bypass was attempted.

Private Studio controls cannot be truthfully marked tested until:
1. backend canonical CORS fix is deployed;
2. frontend repair is deployed to canonical production;
3. an authorized operator credential is supplied to the Playwright audit environment.

When supplied, the checked-in Playwright suite walks every enabled safe Studio button and skips/guards labels matching paid generation, publishing, launch, activation, deletion, checkout, purchase, and upgrade.

### BB-PW-009 — P1 product-contract drift — legacy paid-pass UI remains in Studio Create

Current Create surface still contains legacy language/routes around:
- active paid pass
- Ad Credits
- `Start with a paid test pass`
- `/pricing`

This conflicts with the current public one-time private-install position. The backend itself uses a server-owned wallet/allowance and explicit approval contract.

Do not cosmetically remove this until the installed-operator wallet-selection/provisioning path is reconciled end-to-end; otherwise the UI could look fixed while execution remains coupled to the legacy trial cookie.

### BB-PW-010 — P1 dependency audit

`npm audit` reports one high-severity transitive `browserslist` advisory with a fix available:
- GHSA-c83g-rgw3-j3cx
- GHSA-73wf-gq98-2v4g

No critical advisories were reported.

## Backend runtime truth

Verified `GET https://stavarai.31.220.58.212.sslip.io/api/health`:

- HTTP 200
- status: ok
- platform: buffer blaster
- media configured: true
- storage configured: true
- ledger backend: supabase
- ledger persistent: true
- ledger canonical: true
- publisher configured: false
- approval gate: true

Publishing is therefore **NOT CONFIGURED**, not broken core functionality.

## Playwright MCP added to the repo

Project config:
- `.mcp.json`
- pinned `@playwright/mcp@0.0.82`
- Chromium
- headless
- isolated context

Agent protocol:
- `docs/PLAYWRIGHT_MCP.md`
- `AGENTS.md` requires browser verification for UI/auth/form/release work.

Deterministic suite:
- `frontend/playwright.config.ts`
- `frontend/e2e/production.spec.ts`
- `frontend/scripts/run-production-playwright.sh`
- `.github/workflows/playwright-production-audit.yml`

The suite records failure screenshots/video/traces and has an optional authenticated operator pass via a runtime-only environment variable.

## Current safe gate

Before claiming production ready:

1. merge/deploy Netlify runtime restoration to the canonical `bufferblaster` project;
2. deploy backend canonical CORS fix;
3. prove canonical homepage is HTTP 200;
4. use an authorized operator password in Playwright;
5. click every safe private Studio control;
6. verify model picker returns real backend models;
7. verify no console/network failures;
8. keep paid generation and publishing guarded unless separately approved;
9. resolve or consciously accept the high-severity dependency advisory;
10. reconcile installed-operator wallet UX vs legacy trial/pass UI.
