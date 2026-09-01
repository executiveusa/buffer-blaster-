# Buffer Blaster production finish PRD

This is the single remaining execution list for Buffer Blaster. Work top to bottom. Do not add features that are not required by these outcomes.

## Operating rules

- Canonical product name: Buffer Blaster.
- Preserve all auth, RLS, secret, human-approval, spend, and publish controls.
- Never print or commit credentials.
- Prefer deletion/reuse/native platform features over new abstractions.
- Every completion claim needs executable evidence.
- If a provider credential is absent or invalid, record the blocker and continue every task that does not depend on it.
- A missing paid-provider credential does not justify weakening the provider contract.
- Real ad activation/spend requires the existing explicit human approval gate. The finisher may create only provider objects that are provably paused/disabled and non-spending.
- Do not fabricate Shopify revenue or provider success.

## Tasks

- [ ] Phase 5: inventory Meta, TikTok, and Shopify production credential presence without printing values; write a sanitized provider matrix.
- [ ] Phase 5: authenticate to every configured provider and verify the intended account/shop identity.
- [ ] Phase 5: for each configured paid provider, prove the smallest safe paused/disabled create -> readback -> rollback path with zero spend; if unsafe or unsupported, record not_run and the exact reason.
- [ ] Phase 5: verify Shopify Admin access, required webhook registrations/callback, HMAC validation, and duplicate-delivery idempotency without synthetic revenue.
- [ ] Phase 5: persist provider verification receipts and mark live_verified=true only for providers whose complete required proof passed.
- [ ] Phase 5: select the smallest fully verified provider subset for the first capped production proof; one paid provider per variant remains mandatory.
- [ ] Phase 6: implement and test the Hermes -> Buffer Blaster machine-readable handoff for SCAN/QUALIFY/MODEL -> PROVE/JUDGE -> human APPROVE -> TEST/VERIFY -> CLOSE/ITERATE/KILL/COMPOUND without merging Hermes into this repository.
- [ ] Phase 6: add durable receipts/correlation IDs so the round trip is observable and retry-safe rather than inferred from chat text.
- [ ] Phase 6: prove one non-spending end-to-end Hermes round trip against production and capture sanitized evidence.
- [ ] Phase 7: create the first-production-proof manifest: one offer, one landing page, control/challenger, one paid provider per variant, one KPI, explicit capped budget field, kill threshold, rollback plan, and attribution window.
- [ ] Phase 7: prove the full flow in non-spending/paused mode: approval -> provider hierarchy -> readback -> Shopify attribution plumbing -> evaluator -> PASS/ITERATE/KILL decision -> Hermes receipt.
- [ ] Phase 7: keep actual paid activation blocked unless the existing explicit human approval and a concrete budget ceiling are present. Production-ready completion does not require inventing approval or spend.
- [ ] Product cleanup: remove remaining user-visible Stavarai/PostaTees identity from public health/status/UI/URLs where controlled by this repo; compatibility install paths and internal container names may remain when changing them adds deployment risk.
- [ ] Product cleanup: run a Humanizer-style copy pass over public marketing/onboarding/help text: remove AI filler, inflated claims, fake-candid language, redundant headings, and unsupported claims without changing facts or product behavior.
- [ ] Product cleanup: run a Ponytail-style implementation pass: delete dead abstractions, reuse installed/native capabilities, and reduce code only where security, validation, accessibility, observability, and error handling remain intact.
- [ ] Production verification: run Python tests, frontend security/lint/build/route smoke, fresh schema proof, production compose/container smoke, self-host preflight, public HTTPS health, API-to-Supabase proof, worker health, and rollback checks.
- [ ] Production verification: inspect all unresolved PR review threads/issues introduced by this finish branch and resolve every substantive blocker.
- [ ] Final gauntlet: compare Buffer Blaster side-by-side with https://www.adpanel.io/ at desktop and mobile for onboarding clarity, dashboard hierarchy, creative workflow, approvals/status, experiment visibility, trust, responsiveness, and perceived speed. Use a separate critic context. Exit only when Buffer Blaster wins or every remaining difference is explicitly non-applicable to Buffer Blaster's product scope.
- [ ] Final gate: reconcile this entire PRD and GATES.production.md against the current repository and deployed production. Do not report production complete while any runnable gate is unverified.

## Source patterns intentionally adapted

- Completion ledger / re-verification: https://github.com/Leonxlnx/unlazy
- Minimal necessary implementation: https://github.com/DietrichGebert/ponytail
- Plain, non-AI-sounding public prose: https://github.com/blader/humanizer
- Autonomous task execution / resume: https://github.com/michaelshimeles/ralphy
- Builder + independent binary critic against a named quality bar: https://github.com/robonuggets/gauntlet-loop (CC BY 4.0; technique packaged by RoboNuggets, credited in the source project)
