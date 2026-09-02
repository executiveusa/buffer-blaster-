# Gemini Final Polish / Runtime Handoff

Use this only after PR #52 is merged to `main`.

## Objective
Deploy and independently verify the final private-creative-infrastructure positioning without redesigning the product or bypassing safety controls.

## Repository
`https://github.com/executiveusa/buffer-blaster-.git`

## Server
Historical install path: `/opt/stavarai`

## Rules
- Pull the exact merged `main` SHA and record it.
- Never print, copy into reports, or commit secret values.
- Do not activate real ad spend or public publishing.
- Do not silently edit production code. If a defect needs code, create a branch + PR.
- Optional providers remain unverified unless real account authentication/readback succeeds.

## 1. Deploy / health
1. Preserve the existing self-hosted Supabase network/configuration.
2. Rebuild/recreate only Buffer Blaster application containers as required.
3. Run `scripts/selfhost/preflight.sh` and `scripts/selfhost/smoke.sh`.
4. Verify public `/api/health` says `platform: buffer blaster`.
5. Record rollback SHA before deployment.

## 2. ICM cold-agent walk test
Run `docs/ICM_WALK_TEST.md` with a fresh agent/context. It must route normal tasks using root `AGENTS.md`, root `CONTEXT.md`, and at most one relevant area context/reference per question. Record PASS/FAIL and every unnecessary repository-wide search.

## 3. REST / MCP / CLI walk test
Using legitimate operator authentication without printing it:
- REST `/api/studio/status` succeeds.
- unauthenticated MCP privileged call fails closed.
- authenticated MCP `initialize` succeeds and returns `serverInfo.name=buffer-blaster`.
- authenticated MCP `tools/list` succeeds.
- CLI `python -m cli.blaster status` succeeds against the same API.
- CLI `mcp-info` identifies Buffer Blaster.
- one no-spend UGC plan succeeds.
- unapproved paid execution is rejected.
- no secret value appears in stdout/stderr/report.

## 4. Budget safety
Prove the server-owned generation wallet prevents an agent/browser from exceeding the available provider-cost budget. Use a safe non-spending/insufficient-wallet test. The media provider must not be called when reservation fails.

## 5. Optional Buffer publishing adapter
Only if legitimate `BUFFER_API_KEY` already exists in private server configuration and the operator intended this integration:
- set/select `PUBLISHING_PROVIDER=buffer` privately;
- authenticate and read organization/channels;
- do not create or publish a post;
- report `configured=true`, identity/read proof, and channel count without secret values.
If credentials are absent, report `configured=false`; this is not a core blocker.

Shopify, Meta, and TikTok follow the same truth rule: absence of live credentials is not a core blocker and must not be presented as live verification.

## 6. Frontend deployment truth
Identify the frontend deployment that serves this exact merged SHA. The previously verified frontend hostname was `https://stavarai-platform.vercel.app`; do not assume it updated. If Vercel CLI credentials on the server legitimately control that project, deploy the merged frontend and record deployment/alias evidence. Otherwise report the exact access blocker rather than substituting `buffer-blaster.vercel.app`, which is stale.

## 7. Browser / Collins / MaxFusion proof
Follow `docs/MAXFUSION_GAUNTLET.md` and the project's Collins protocol.
Capture Buffer Blaster at 320, 390, 430, 768, 1024, and 1440 widths:
- homepage first viewport + full page;
- `/pricing` (Access);
- Studio overview;
- Studio create flow;
- one approval/budget-limited state.

Verify:
- Buffer Blaster is the public product name; Studio is the workspace;
- no public $19/$49/$99/$199/token-plan storefront;
- no Social Studio identity on public surfaces;
- zero horizontal overflow;
- readable contrast and visible focus;
- sufficient touch targets;
- no console/runtime errors;
- no browser-visible secrets.

Then independently compare equivalent Buffer Blaster screenshots against `https://maxfusion.ai/` for category clarity, workflow comprehension, credibility, agent access, mobile hierarchy, and distinctiveness. Do not copy MaxFusion.

## 8. Security pass
Check browser bundles, source maps, network responses, logs, and repository history reachable from this release for accidental secret material. Verify admin/operator and paid/publish paths fail closed without proper authorization.

## Final report
Write a sanitized report to:
`/tmp/buffer-blaster-final-polish-report.md`

Return:
- deployed SHA;
- rollback SHA;
- frontend URL + SHA proof;
- backend health proof;
- ICM walk-test result;
- REST/MCP/CLI result;
- budget fail-closed result;
- Buffer optional integration status;
- mobile/Collins score;
- MaxFusion comparison and single biggest remaining gap;
- security result;
- blockers.

Use only these overall statuses:
- NOT READY
- PREVIEW VERIFIED
- PRODUCTION VERIFIED
