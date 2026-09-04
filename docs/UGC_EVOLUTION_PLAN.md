# Buffer Blaster UGC Evolution Plan

**Decision:** APPROVED FOR IMPLEMENTATION  
**Planning date:** 2026-09-03  
**Planning branch:** `plan/ugc-reference-architecture-2026-09-03`  
**Reference manifest:** `docs/UGC_REFERENCE_MANIFEST.md`  
**Implementation starts only after this planning PR merges.**  

This is the complete build order for evolving Buffer Blaster from a working UGC-capable creative system into private, provider-neutral creative infrastructure for Max Digital Media and client operating systems.

No feature code belongs in this planning branch.

---

## 1. Outcome

Buffer Blaster should let an operator or approved agent move from **evidence to creative to proof** without assembling separate UGC, avatar, editing, clipping, publishing, and attribution subscriptions.

The desired outcome is not "generate AI video." It is:

> **Take a product, a source of creative signal, and a goal; understand what is worth testing; make controlled creative variants; preserve their lineage/cost/approval; and learn from real evidence.**

The highest-leverage commercial use remains internal/client delivery:
- managed creative engine inside a high-value client engagement;
- private dedicated install for a team/client;
- optional Studio access as part of the service;
- REST/MCP/CLI access for approved agents;
- optional Buffer/Shopify/paid-media connections around the client outcome.

Do not reintroduce low-ticket token-subscription positioning to justify these capabilities.

---

## 2. The black-swan capability

### Reference Ad → Strategy Receipt → Controlled Variants → Test → Learn

This is the first major capability to build.

A user or agent supplies:
- a reference ad/video or URL that the workspace has a right to analyze;
- the client's product/offer;
- brand/customer context;
- target outcome/channel.

Buffer Blaster returns a **strategy receipt**, not a clone:
- opening hook mechanic;
- customer tension/problem;
- angle;
- narrative structure;
- pacing pattern;
- creator archetype;
- proof device;
- shot logic;
- product reveal placement;
- CTA mechanic;
- claims/risks to avoid;
- why the strategy may work for this client;
- what must change to make the output original and on-brand.

Then the operator can request controlled variants such as:
- same strategy, different hook;
- same hook, different creator archetype;
- same angle, different proof device;
- same structure, raw UGC vs creator-premium finish.

### Why this comes first

Generic UGC generation is becoming commodity infrastructure. The leverage is deciding **what to make and what variable is being tested**, then preserving evidence so the next round improves. Lazynext's Reference-to-Ad concept, OpenShorts' hook/script flow, and the AI YouTube Shorts Generator's highlight/virality scoring are references; Buffer Blaster's differentiator is the governed experiment and receipt layer around them.

---

## 3. Architecture law

### Keep

The following existing Buffer Blaster systems remain authoritative:
- FastAPI backend;
- self-hosted Supabase `buffer_blaster` schema;
- Redis sessions/rate limits/server-owned generation wallet;
- money-loop experiment and attribution model;
- human approval gates;
- Fal provider path;
- worker/runtime topology;
- Hermes bridge;
- REST `/api/*`;
- MCP `/api/mcp`;
- CLI `python -m cli.blaster`;
- Studio/browser UI;
- optional Buffer downstream publishing adapter.

### Add behind those systems

```text
SOURCE SIGNAL
  reference ad / URL
  product assets
  creator assets
  client long-form media
        │
        ▼
CREATIVE INTELLIGENCE
  analyze → strategy receipt → test variable
        │
        ▼
UGC PLAN
  product refs + creator ref + script + shot plan + finish mode
        │
        ▼
PROVIDER ROUTER
  hosted premium / hosted fast / sovereign local
        │
        ▼
TAKES + FINISHING
  raw output → crop → captions → B-roll → finish
        │
        ▼
CANONICAL RECEIPT
  inputs + consent + model + cost + approval + artifact hash
        │
        ▼
EXPERIMENT / DISTRIBUTION / ATTRIBUTION
  test → evidence → next decision
```

Provider services never become the canonical system of record.

---

## 4. Normalized media contracts

Implementation should introduce **contracts before providers**.

### 4.1 `CreativeSource`
Represents evidence/media entering the system.

Minimum fields:
- `source_id`
- `workspace_id`
- `kind`: product_image, creator_image, reference_ad, source_video, source_audio, brand_asset, url
- `uri` or storage key
- `sha256`
- `mime_type`
- `owner/rights_state`
- `consent_state` when a person/voice is involved
- `provider_export_allowed`
- `created_at`

### 4.2 `StrategyReceipt`
Canonical result of reference/source analysis.

Minimum fields:
- `receipt_id`
- `workspace_id`
- source refs/hashes
- hook mechanic
- angle
- customer tension
- structure
- pacing
- creator archetype
- proof device
- shot logic
- CTA mechanic
- claims/brand risks
- originality transformations
- recommended test variable
- model/provider provenance
- created_at

### 4.3 `UGCPlan`
The provider-neutral request before spending/generation.

Minimum fields:
- `plan_id`
- `workspace_id`
- product refs
- creator/avatar ref
- optional setting/style refs
- strategy receipt ref
- script
- shot plan
- aspect ratio/duration
- finish mode
- provider preference: `auto`, `fast`, `premium`, `sovereign`
- estimated cost ceiling
- approval state
- consent/rights refs
- idempotency key

### 4.4 `MediaTake`
One generated or transformed media result.

Minimum fields:
- `take_id`
- `plan_id`
- parent take/source refs
- provider
- model/version
- request/job ID
- actual cost
- output storage key
- artifact hash
- dimensions/duration
- generated/derived state
- finish state
- receipt/provenance ref
- created_at

Multiple takes must never overwrite one another.

### 4.5 `ProviderCapabilities`
Every renderer exposes a normalized capability description:
- text-to-video
- image-to-video
- reference images count
- lip sync
- audio driven
- body motion
- local/hosted
- supported ratios/durations
- estimated cost/latency
- consent requirements
- commercial-use status
- health/readiness.

This is how the Studio/agent asks for an outcome without hardcoding a vendor/model.

---

## 5. Provider architecture

Implement one provider interface:

```text
capabilities()
plan_and_estimate(request)
submit(approved_request)
status(job_ref)
result(job_ref)
cancel(job_ref)
health()
```

Every implementation must return normalized cost/provenance and must be safe to retry with the same idempotency key.

### Tier A — existing/hosted
1. **Fal** — keep current production path; first adapter to the normalized contract.
2. Additional hosted models (Seedance/Veo/etc.) — only when a real client/workload justifies them.

### Tier B — sovereign R&D
Order of investigation:
1. **EchoMimic V3** — preferred first local avatar candidate.
2. **OmniAvatar** — body-motion candidate.
3. **LivePortrait** — portrait retargeting only after commercial-safe detector replacement.
4. **HeyGem** — only after explicit license/commercial and consent review.

Do not require a local GPU model for the core Buffer Blaster release. Sovereign rendering is a provider option, not a new architectural center.

---

## 6. Finish modes

Expose simple outcomes, not cinematography jargon.

### `raw_ugc`
- authentic creator framing;
- minimal grading;
- captions optional;
- no unnecessary cinematic treatment.

### `creator_premium`
- cleaner framing/crop;
- captions/hook treatment;
- light B-roll/product inserts;
- restrained polish.

### `product_cinematic`
- intentional shot sequence;
- premium lighting/camera grammar;
- product-focused finishing;
- AI Cinema Studio Engine is a reference.

### `editorial_brand`
- stronger composition/type/motion system;
- suitable for premium brand campaigns;
- must still preserve original client identity rather than apply a generic style preset.

The default for UGC remains `raw_ugc`. More polish is not automatically better.

---

## 7. Long-form repurposing path

After the Reference-Ad and multi-reference UGC paths are stable, add source repurposing.

Input examples:
- podcast;
- founder interview;
- testimonial;
- Zoom call;
- product demo;
- coach/client video;
- webinar.

Pipeline:
1. ingest source with hash/rights metadata;
2. transcribe;
3. identify candidate moments;
4. score hooks/value/emotion/quotability/conflict/revelation;
5. deduplicate overlapping moments;
6. generate 9:16 crop plan;
7. subtitles/hook overlay plan;
8. operator approves candidates;
9. render clips;
10. optionally feed a candidate into the creative experiment engine.

Source lineage must remain attached to every derived clip.

---

## 8. Agent-native skill pack

Create provider-neutral Buffer Blaster skills inspired by `Generative-Media-Skills`, but keep ICM and existing REST/MCP/CLI as the authority.

Initial skills:

1. `reference-ad-analysis`
   - inspect allowed source;
   - create StrategyReceipt;
   - no generation/spend.

2. `ugc-plan`
   - assemble references/script/shot plan;
   - estimate cost;
   - no paid generation.

3. `ugc-generate`
   - requires valid rights/consent;
   - requires explicit approval;
   - server wallet reserves budget atomically;
   - creates MediaTake receipt.

4. `ugc-takes`
   - list/read lineage and artifacts;
   - no spend.

5. `repurpose-source`
   - transcript/highlight/crop planning;
   - render only after approval where paid action occurs.

6. `publish-via-buffer`
   - optional downstream distribution;
   - explicit publishing approval remains required.

Every skill must be callable through the same governed backend and discoverable by a cold agent through the ICM router.

---

## 9. Human / agent safety controls

### 9.1 Spend
Existing server wallet remains the source of truth.

Before any provider request capable of incurring cost:
1. workspace budget active;
2. plan has positive maximum cost;
3. human/authorized approval is present;
4. budget reservation succeeds atomically;
5. provider call begins;
6. actual cost reconciles to receipt;
7. reservation releases/settles deterministically.

Agents cannot:
- raise their own ceiling;
- bypass a zero/insufficient wallet;
- switch to a more expensive provider beyond the plan ceiling;
- retry into duplicate spend.

### 9.2 Face / voice
Before cloning or animating an identifiable person's face or voice:
- rights/consent state must be explicit;
- source artifact must be recorded;
- client/workspace must permit that provider export;
- generation receipt must carry the consent reference.

### 9.3 Reference creative
The analysis layer may learn strategy and mechanics. It must generate an originality transformation plan. It must not instruct a provider to reproduce protected logos, exact scripts, distinctive copyrighted shots, or deceptive identity cues.

### 9.4 Provider data
Workspace policy determines which providers may receive which source assets. Private/local routing can be required for sensitive work.

---

## 10. Canonical data and storage changes

Do not create schema until implementation begins and the existing production schema has been re-inspected.

Expected additive domain objects:
- `creative_sources`
- `strategy_receipts`
- `ugc_plans`
- `media_takes`
- optional `media_rights_receipts`

Prefer foreign keys into existing workspace/client/campaign/experiment/content structures where live ID types allow it. Do not repeat the earlier mistake of assuming production ID types from stale migrations.

Generated binaries belong in private/self-hosted storage by default; Supabase rows carry metadata, lineage, hashes, provider job IDs and receipts.

No destructive migration is planned.

---

## 11. Studio UX

Do not build a giant AI-media dashboard.

### Primary flow

```text
What are we making?
    ↓
What signal are we using?
    ↓
What is the plan?
    ↓
What will it cost?
    ↓
Approve
    ↓
Takes
    ↓
Choose / test / publish
```

### Entry cards
Keep the first release to three high-value entry points:
- **Remake the strategy** — reference ad → original controlled variants.
- **Make UGC** — product + creator + angle → takes.
- **Repurpose footage** — long-form source → candidate shorts.

Do not expose model names unless the user opens an advanced/provider detail.

### Multiple takes
Use a simple take strip/grid showing:
- thumbnail/video;
- take number;
- finish mode;
- cost;
- approval/result state;
- lineage/provenance drawer.

No node graph in the normal Studio.

---

## 12. Implementation phases

### Phase U0 — Architecture lock (this PR)
**Goal:** provenance and implementation plan before code.

Deliverables:
- immutable reference manifest;
- license/commercial hard stops;
- full implementation sequence;
- ICM routing update;
- no feature code.

Exit:
- planning PR merged;
- cold agent can find both docs from `AGENTS.md`;
- changed files are documentation/router only.

### Phase U1 — Canonical contracts + receipts
**Goal:** provider-neutral foundation.

Deliverables:
- source/strategy/plan/take domain contracts;
- additive DB migration after live schema inspection;
- repositories/services;
- REST read/write paths;
- MCP/CLI discovery and no-spend planning;
- idempotency tests;
- provenance/security tests.

No new paid model required.

Exit:
- a no-spend UGC plan can be created/read identically via REST/MCP/CLI;
- all receipts persist in self-hosted Supabase;
- rights and cost ceiling are mandatory where applicable.

### Phase U2 — Reference-Ad Intelligence
**Goal:** build the black-swan feature before adding more render engines.

Deliverables:
- reference ingest;
- strategy deconstruction;
- originality transformation plan;
- 3 controlled variant plans;
- strategy receipt UI;
- skill/MCP/CLI route.

Exit:
- given one approved reference and a client product, system produces three distinct testable plans without copying the reference's protected surface expression;
- no provider spend is necessary to pass U2.

### Phase U3 — Multi-reference UGC Factory
**Goal:** normalize the current Fal path into the new plan/take architecture.

Deliverables:
- product/creator/style refs;
- Fal provider adapter behind normalized interface;
- estimate → approve → reserve → submit → receipt;
- multiple takes;
- retry/dedupe/cancel;
- owned artifact storage;
- Studio takes UI.

Exit:
- one plan can create multiple takes without duplicate spend;
- actual provider/model/cost/artifact hash recorded;
- no generated asset depends on an ephemeral third-party URL after ingestion.

### Phase U4 — Deterministic edit/finish layer
**Goal:** own the post-production step.

Deliverables:
- crop/aspect conversion;
- captions;
- hook/title treatment;
- B-roll/product inserts;
- raw_ugc + creator_premium modes first;
- Remotion/FFmpeg receipt of edit parameters.

Exit:
- same take can be re-finished deterministically;
- original take is never overwritten;
- mobile/vertical output passes playback and accessibility checks.

### Phase U5 — Long-form Repurposing
**Goal:** turn existing client media into test inventory.

Deliverables:
- source ingest/transcript;
- highlight scoring;
- dedupe;
- crop/subtitle plans;
- candidate review;
- derived clip lineage.

Exit:
- client source video can yield ranked candidate clips while preserving source timestamps/hash and approval state.

### Phase U6 — Sovereign avatar provider R&D
**Goal:** reduce paid-provider dependency where it actually matters.

Order:
1. EchoMimic V3 spike;
2. OmniAvatar spike;
3. LivePortrait spike with commercially permitted detector;
4. HeyGem only after licensing approval.

This is a benchmark, not automatic integration.

Measure:
- GPU requirement;
- cold/warm latency;
- cost per usable 5/10/30 seconds;
- identity stability;
- body motion;
- lip sync;
- artifact rate;
- operator preference;
- commercial/license status.

Exit:
- integrate only providers that beat hosted routing on a documented client use case.

### Phase U7 — Premium finishing + distribution proof
**Goal:** selectively add product_cinematic/editorial_brand and prove downstream handoff.

Deliverables:
- premium finish recipe;
- Buffer publishing read/prepare path;
- Shopify/client context handoff where configured;
- experiment linkage and evidence loop.

Exit:
- a chosen take can move through approval to optional distribution while retaining end-to-end provenance.

### Phase U8 — Gauntlet + client proof
**Goal:** prove this is leverage, not a feature pile.

Run:
- ICM Walk Test;
- security/secrets audit;
- REST/MCP/CLI parity;
- budget bypass attempts;
- consent/rights tests;
- mobile/browser audit;
- reference-ad originality review;
- provider cost/latency matrix;
- one real internal/client creative cycle with explicit approval and capped spend.

Release only if the operator can explain the workflow in seconds and an agent can discover it without repository archaeology.

---

## 13. What we deliberately do not build

Not approved in this plan:
- public creator marketplace;
- public social feed;
- token/credit subscription storefront;
- generic node editor as default UI;
- automatic scraping/cloning of public people;
- provider-specific UI forks;
- autonomous budget increases;
- autonomous ad spend/publishing without explicit approval;
- a second database/ledger for media jobs;
- copying all upstream repos into this monorepo;
- bundling restricted model weights because an upstream app happens to use them.

---

## 14. Build-vs-reference decisions

| Area | Decision |
|---|---|
| Governing API/data/approval/budget | **Keep Buffer Blaster** |
| Reference-ad strategy analysis | **Build natively; learn from Lazynext/OpenShorts/shorts scoring** |
| Multi-reference UX/contracts | **Build natively; learn from Open-AI-UGC/UGC.AI** |
| Hosted generation | **Adapter; keep Fal first** |
| Local avatar generation | **Provider plugins after benchmarks** |
| Captions/crop/edit | **Own deterministic layer; learn from OpenShorts/MoneyPrinterTurbo** |
| Premium cinema | **Optional finish recipes; learn from AI Cinema Studio Engine** |
| Multiple takes/project lineage | **Build into canonical receipts; learn from Backblaze sample** |
| Agent skill ergonomics | **Build into existing REST/MCP/CLI; learn from Generative Media Skills** |
| Workflow graph | **Reference only; defer** |

---

## 15. Acceptance standard for every implementation slice

A slice is not complete until:
1. closest ICM `CONTEXT.md` remains accurate;
2. provenance points to exact upstream path/SHA when used;
3. license/model terms are recorded;
4. tests cover happy path and fail-closed path;
5. no secret moves to browser/client code;
6. agent cannot bypass budget/approval;
7. idempotent retry is proven for consequential calls;
8. canonical receipt is persisted;
9. REST/MCP/CLI parity is checked when capability is agent-facing;
10. UI is mobile-readable and does not expose unnecessary provider complexity;
11. production deployment/rollback evidence exists before a live claim;
12. upstream code is never called "integrated" merely because it was studied.

---

## 16. Approval

**APPROVED FOR IMPLEMENTATION.**

The approved order is:

**U0 provenance lock → U1 contracts → U2 Reference-Ad Intelligence → U3 multi-reference UGC → U4 deterministic finishing → U5 source repurposing → U6 sovereign avatar benchmarks → U7 premium/distribution proof → U8 final gauntlet.**

The first implementation PR after this planning PR merges must be **U1 only**. It must not jump directly to cloning an upstream UI or installing five model stacks.

This sequencing preserves the thing Buffer Blaster already does better than a pile of UGC apps: one governed creative loop with client context, human control, budget truth, evidence, and agent access.
