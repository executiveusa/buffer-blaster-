# Buffer Blaster Autonomous Finish Loop

This is the final autonomous engineering contract for Buffer Blaster.

## Goal
Finish the highest-leverage internal creative-infrastructure product without turning it back into a low-ticket SaaS. Every phase must be independently verified, merged to `main`, then re-read from the new `main` before the next phase starts.

## Engine
- **Ralphy** (`michaelshimeles/ralphy`) is the execution loop.
- **Unlazy** (`Leonxlnx/unlazy`) supplies acceptance-ledger discipline: incomplete work must remain visible and every completion claim needs executable evidence.
- **Gauntlet Loop** (`robonuggets/gauntlet-loop`) supplies the final independent builder/critic comparison. The visual/product bars are AdPanel for clarity and Collins-level standards for identity, hierarchy, restraint, and mobile craft.
- Existing repository law in `AGENTS.md`, `EMERALD_TABLETS.md`, area `CONTEXT.md` files, human approval controls, RLS, spend/publish gates, and ICM boundaries remain authoritative.

## Open-source UGC research set
Study before implementing. Borrow patterns, not identity. Do not copy code unless its license is compatible and provenance is recorded.

1. `mutonby/openshorts` — UGC/avatar/short-form workflow.
2. `Anil-matcha/Open-AI-UGC` — multi-model UGC job UX and reference handling.
3. `Lazynext-Platform/Lazynext` — ecommerce/reference-ad remake workflows.
4. `poptechstudio/ai-cinema-studio-engine` — shot planning/finishing/SOP patterns.
5. `HarderSoftware/HeyGem.ai`, `Omni-Avatar/OmniAvatar`, `antgroup/echomimic_v2`, `KlingAIResearch/LivePortrait` — optional sovereign avatar-provider research only; never claim runtime support until an adapter is actually tested.
6. `SamurAIGPT/AI-Youtube-Shorts-Generator` — long-form-to-short-form repurposing patterns.

## Phase order
1. UGC provider + provenance contract.
2. Reference-ad intelligence/remix flow.
3. Creator/avatar provider layer and cost-aware routing.
4. Short-form repurposing pipeline.
5. Buffer/Shopify/API/MCP/CLI interoperability.
6. Auth/onboarding/budget/security hardening.
7. ICM walk test + README/docs.
8. Final code review, browser/mobile gauntlet, production deployment and report.

## Merge law
For every phase:
1. reset from current `origin/main`;
2. create `autofinish/phase-NN-*`;
3. run Ralphy/Gemini only against that phase PRD;
4. do not allow unchecked PRD tasks to disappear without evidence;
5. run deterministic local gates;
6. push branch and open/reuse a PR;
7. wait for GitHub checks;
8. treat known external review-provider outages as external evidence, never as a clean review;
9. squash-merge only after substantive checks pass;
10. fetch/reset to the new `origin/main`;
11. run smoke verification again;
12. continue automatically.

## Stop conditions
Do not stop for ordinary coding decisions, flaky first attempts, or one failed test. Diagnose, repair, rerun.

Stop only for:
- a secret/credential genuinely absent and required for the next safe proof;
- ambiguous client/provider identity that could cause the wrong account to be touched;
- real spend/publish/contractual action lacking explicit human approval and a concrete ceiling;
- destructive migration/data action without an approved rollback path;
- legal/license ambiguity that would require copying incompatible source code.

Independent phases that do not need the blocked resource must continue.

## Final state
The loop may print `AUTONOMOUS_FINISH_VERIFIED` only when all eight phase receipts exist, final review is complete, production smoke is green, no known high/critical security finding remains, REST/MCP/CLI walk tests pass, and the browser/mobile gauntlet receipt is present.
