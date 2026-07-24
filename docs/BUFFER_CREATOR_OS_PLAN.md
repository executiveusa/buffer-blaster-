# Buffer Blaster Creator OS — Brownfield Productization Plan

Status: ACTIVE
Mode: Brownfield
Branch: `feature/buffer-creator-os-v1`
Baseline: `9fdb6ec6bd00f659881d8c6de336e7e6aa64f099`

## Outcome
Ship a sellable creator-facing Buffer Blaster prototype that lets a young creator describe what they want to make, receive a small set of relevant creative cards, adapt a selected recipe, save/export it as an ICM-compatible agent pack, and access the same capability through an API.

## Target
Primary: young independent creators who want control of their prompts, assets, AI providers, workflows, and publishing stack.
Secondary: indie SaaS builders and agent developers who want a callable creative-workflow API.

## Constraints
- Extend the existing Buffer Blaster monorepo. Do not create a second SaaS.
- Preserve existing production behavior until the new slice is independently verified.
- No destructive Supabase changes without a namespaced schema/migration and rollback.
- Preserve provenance and license metadata for every imported upstream prompt/workflow.
- No secret values in Git, browser bundles, logs, or public API responses.
- Keep the LLM/provider layer vendor-agnostic.
- Do not load a whole prompt corpus into agent context. Search -> retrieve -> execute.
- No publishing or external account action without explicit user approval.
- Every phase must have a rollback point and proof artifact.

## Proof required for V1
1. Existing main remains recoverable at the recorded baseline.
2. Frontend build passes.
3. Existing backend/API tests remain green.
4. A creator can enter an intent and receive 3 relevant cards.
5. A card can be opened, adapted, saved locally/in demo mode, and exported as an ICM pack.
6. API returns the same card schema as the UI consumes.
7. Every imported card exposes source repo, source path/URL, source commit/hash when known, and license status.
8. No critical accessibility or obvious secret/security regression.
9. A production/preview deployment can be rolled back to the previous READY deployment.

## Commercial value
Immediate validation offer: Founding Creator access.
Initial hypothesis: creators will pay for ownership and workflow control, not merely a prompt gallery.

Core promise: **Your ideas. Your files. Your audience. Your AI.**

Primary loop: **Discover -> Create -> Save/Export -> Publish later**.

---

# Product architecture

## Public product: Buffer Blaster
Buffer Blaster becomes the creator control plane. Existing private/internal content-operations capabilities remain implementation details and must not leak into public surfaces.

## Three product primitives
1. **Cards** — discoverable creative recipes/prompts/workflows.
2. **ICM Workflows** — inspectable filesystem-oriented agent instructions and artifacts.
3. **API** — the same discovery/remix/export capabilities callable by agents and SaaS products.

## Initial creator journey
1. Open Buffer Blaster.
2. Answer: `What do you want to make?`
3. Receive 3 relevant cards, not hundreds of results.
4. Open one card and understand outcome, inputs, supported models, source/provenance, and estimated complexity.
5. Adapt the card using creator/project context.
6. Save to a collection or export an ICM pack.
7. Later phases may generate/publish/measure, but those are not required for the first sellable slice.

---

# ICM implementation contract

The implementation follows the five-layer Interpretable Context Methodology:

- Layer 0: global identity (`AGENTS.md` / workspace identity)
- Layer 1: routing (`CONTEXT.md`)
- Layer 2: stage contract (`stages/<nn_name>/CONTEXT.md`)
- Layer 3: stable reference/factory (`references/`, `_config/`, `shared/`)
- Layer 4: per-run working artifacts (`output/`, run-specific inputs)

Design rules:
- One stage, one job.
- Plain text/JSON are portable interfaces.
- Load only context needed for the current stage.
- Every stage output is inspectable/editable.
- Configure the factory, not each product run.

## Portable export shape

```text
buffer-blaster-agent-pack/
├── AGENTS.md
├── CONTEXT.md
├── manifest.json
├── stages/
│   ├── 01_discover/
│   │   ├── CONTEXT.md
│   │   ├── references/
│   │   └── output/
│   ├── 02_adapt/
│   └── 03_create/
├── _config/
├── shared/
└── README.md
```

---

# Canonical data model

## PromptCard

```ts
interface PromptCard {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  subcategory?: string;
  mediaType: "image" | "video" | "text" | "workflow";
  prompt: string;
  tags: string[];
  modelHints: string[];
  previewAssets: string[];
  requiredInputs: string[];
  requiresReference: boolean;
  icmPath: string;
  qualityScore?: number;
  source: {
    repo: string;
    path?: string;
    url?: string;
    commit?: string;
    author?: string;
    license: string;
    licenseVerified: boolean;
    contentHash: string;
  };
}
```

## Initial categories
- Images
- Video
- Social
- Brand
- Writing
- Research
- Agents
- Workflows

---

# Execution phases

## Phase 0 — Baseline and rollback [LOCKED]
- Record baseline commit.
- Confirm repository permissions.
- Confirm open PR state.
- Create isolated feature branch.
- Record canonical Vercel candidates and rollback deployments.

Exit proof:
- Branch exists from exact main SHA.
- Existing production deployments remain untouched.

## Phase 1 — Product/deployment identity normalization
Goal: remove ambiguity between Buffer Blaster and Stavarai deployment identities without destroying rollback history.

Tasks:
- Treat `buffer-blaster-` as canonical source repo.
- Determine canonical Vercel target for public creator product.
- Preserve existing Stavarai deployment until new public slice passes preview proof.
- Add explicit environment/product identity contract to docs/config.

Exit proof:
- One documented source-of-truth mapping: repo -> preview -> production.

## Phase 2 — Library ingestion foundation
Goal: ingest public upstream prompt libraries with provenance, licensing, dedupe, and deterministic normalization.

Tasks:
- Add upstream registry.
- Add canonical `PromptCard` schema.
- Build deterministic importer adapters.
- Preserve original source references.
- Hash normalized content for dedupe.
- Quarantine items with unknown/ambiguous license instead of publishing them.
- Start with a bounded seed set before bulk import.

Exit proof:
- Seed corpus normalizes into valid cards.
- Re-running importer is idempotent.
- No duplicate IDs/content hashes.

## Phase 3 — ICM compiler/exporter
Goal: convert cards/collections/workflows into portable agent packs.

Tasks:
- Build Layer 0-4 templates.
- Build manifest generator.
- Add export validation.
- Keep output vendor-neutral.

Exit proof:
- A selected card exports a complete portable ICM folder/ZIP structure.

## Phase 4 — Creator card discovery UI
Goal: deliver the YouMind-inspired but task-first card experience.

Tasks:
- Replace/extend public landing with creator positioning.
- Add intent input: `What do you want to make?`
- Add card grid/gallery.
- Return top 3 initial results.
- Add card detail state.
- Add clear source/provenance disclosure.

Exit proof:
- A first-time user can understand the product and reach a usable card without documentation.

## Phase 5 — Search and ranking API
Goal: UI and agents use one retrieval engine.

Endpoints:
- `POST /v1/discover`
- `GET /v1/cards/{id}`
- `POST /v1/prompts/search`

Ranking V1:
- intent/category match
- tags
- supported media/model hints
- quality score
- deterministic tie-breaking

Do not start with complex vector infrastructure. Add embeddings only after lexical/tag retrieval is proven insufficient.

Exit proof:
- API and UI return identical card contracts.

## Phase 6 — Adapt/remix
Goal: make recipes useful to a specific creator without destroying source lineage.

Flow:
- Identify only missing inputs.
- Preserve immutable source recipe.
- Create derived version linked to source.
- Store project/creator context separately from source card.

Endpoint:
- `POST /v1/prompts/remix`

Exit proof:
- User can adapt a card and inspect both original and derived versions.

## Phase 7 — Collections and creator memory
Goal: make the tool sticky without premature complexity.

Tasks:
- Save cards to collections.
- Save creator/project defaults.
- Keep brand/reference context as Layer 3 factory data.
- Keep run-specific requests/assets as Layer 4 working data.

Exit proof:
- Saved collection can be reopened and exported.

## Phase 8 — Supabase persistence
Goal: replace demo/local persistence with portable Postgres-backed persistence.

Proposed namespaced tables:
- `bb_users`
- `bb_creator_profiles`
- `bb_sources`
- `bb_prompt_cards`
- `bb_prompt_versions`
- `bb_collections`
- `bb_collection_items`
- `bb_workflows`
- `bb_workflow_steps`
- `bb_runs`
- `bb_assets`
- `bb_api_keys`
- `bb_usage`

Rules:
- SQL migrations are portable to self-hosted Postgres.
- RLS on exposed tables.
- Never write into unrelated existing project tables.
- Migration rollback documented before production apply.

Exit proof:
- RLS tests pass.
- Schema export applies to clean Postgres/Supabase test environment.

## Phase 9 — A2A / agent access
Goal: let any agent use the same library without the UI.

Interfaces:
- `skill.md` / agent instruction surface
- REST API
- later MCP wrapper if demanded by actual usage

Initial actions:
- `buffer.search()`
- `buffer.get_card()`
- `buffer.remix()`
- `buffer.export_icm()`

Rule: search -> retrieve -> execute; never dump full library into context.

Exit proof:
- An external agent can discover and retrieve a card using documented API/skill instructions.

## Phase 10 — Commercial launch slice
Goal: collect money and usage evidence.

Offer hypothesis:
- Founding Creator: limited launch offer.
- Free discovery layer for acquisition.
- Paid creator ownership/workflow features.
- BYOK/provider control as a future differentiator.
- API pricing only after measured external demand.

Minimum launch instrumentation:
- landing conversion
- search started
- card opened
- card saved/exported
- checkout started/completed

Exit proof:
- A user can understand offer, use core loop, and pay or join founding cohort.

---

# Explicitly parked until core loop proves demand

- full video editor
- Canva replacement
- custom model training
- autonomous swarm orchestration
- marketplace payouts
- complex multi-tenant enterprise RBAC
- blockchain/crypto features
- native mobile apps
- advanced analytics/autoresearch for creator-facing V1

Any one of these requires replacing an active workstream before implementation.

---

# Release gates

A phase can merge only when:
1. Existing tests/build remain green.
2. New capability has a test or deterministic proof.
3. Security/secret exposure check passes.
4. Accessibility has no known critical regression.
5. Rollback is documented.
6. Product scope still serves the core loop.
7. No builder self-approval for final production release.

Recommended release score: >= 8.5/10 across user value, architecture, failure handling, security, taste, sovereignty, and commercial alignment.

---

# Tomorrow-market definition of done

The prototype is market-testable when a creator can:

`Describe intent -> receive 3 cards -> open one -> adapt it -> save/export it -> understand the paid offer.`

Nothing beyond this loop is required before outreach begins.
