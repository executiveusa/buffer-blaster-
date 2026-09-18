# Buffer Blaster — MaxFusion Creative Gauntlet V2

Status: ACTIVE BROWNFIELD SPEC — no production deploy from this document alone.
Classification: SELL (revenue offer/product surface).
Benchmark: https://maxfusion.ai/

## Outcome

Turn Buffer Blaster from a mostly linear UGC factory with a static workflow map into a zero-friction, agent-native creative operating system where a user can move from product truth and references to research, angles, storyboard, generation, composition, evidence, and repeatable batch production without losing Buffer Blaster's spend/publish governance.

## Non-negotiable constraints

- Preserve current backend contracts unless a migration is explicitly specified.
- Preserve explicit human approval before paid generation and publishing.
- Preserve evidence/job receipts and provider-neutral media contracts.
- Do not fabricate social proof, performance results, provider costs, or production state.
- No decorative workflow controls: if a node can be moved/edited/run, its graph/state must persist and map to executable behavior.
- Do not copy MaxFusion proprietary source, design, or copy. Benchmark observable outcomes only.
- Unlicensed third-party source may inform original procedures but is not copied.
- Every release candidate requires rollback and independent review.

## Baseline found in Buffer Blaster

Existing strengths:

- Public Studio, create flow, asset library, moodboards, canvas, campaigns, calendar, analytics, settings.
- No-spend ad planning before paid generation.
- Explicit cost/allowance and human approval gates.
- Canonical reference-asset backend for moodboards.
- Provider-neutral UGC executor and durable receipts.
- UI + REST + MCP + CLI product surfaces.
- Existing design-gauntlet script and release-gate culture.

Current gaps versus the benchmark:

1. Homepage still prioritizes beta/waitlist instead of immediate product value.
2. `/studio/canvas` is a static four-node diagram; node editing is intentionally locked because no persisted executable graph exists yet.
3. Research is not a first-class workflow node connected to reference → angle → generation.
4. Storyboard and creator/product continuity are not first-class visible pre-spend artifacts.
5. No unified compositor/editor flow comparable to research → generation → finishing in one workspace.
6. Batch/variant production is not yet the dominant operating mode.
7. Social proof/performance evidence on the public surface is weaker; only verified evidence may be added.

## Source intake

### `harshith-vaddiparthy/UGC-dashboard` — USE selectively

MIT. Useful patterns:

- React Flow / `@xyflow/react` visible production canvas.
- Canvas visualizes workflow state while server-side orchestration owns execution.
- Explicit node lifecycle: pending / running / completed / failed.
- Persistent workflow runs independent of component animation.
- Server-only provider credentials.
- Replaceable provider boundary.
- Visible failures that preserve user input.
- Credit-free demo path.

Do not transplant its local JSON persistence into multi-user production. Buffer Blaster already has stronger durable backend/storage patterns.

### `joebenscoter86/higgsfield-ugc-workflow` — ADAPT procedure

MIT. Useful decomposition:

- product profile / references
- creative brief
- base character / continuity
- storyboard before expensive generation
- multicut script
- generation
- enhancement/polish

Provider pricing/model details are volatile and must be reverified rather than hardcoded.

### `AKCodez/higgsfield-claude-skills` — CONCEPTS ONLY

No repository license was verified during intake. Do not copy skill text or automation code. Mine only general ideas such as:

- specialized creative-direction families
- batch-session recovery/checkpointing
- explicit pre-generation confirmation
- agent-driven browser workflow patterns

Any production implementation must be original or use a separately licensed source.

### Owner-supplied Gauntlet Loop — ADAPT WITH ATTRIBUTION

CC BY 4.0. Builder and critic are separate. Benchmark must be named/fetchable/comparable. Compare directly, fix the highest-impact defect, rerun until the challenger wins or the dimension is honestly marked unverified.

## Product architecture target

### Graph contract

The flow canvas becomes a projection/control surface over a durable server-owned graph.

Minimum node contract:

- `id`
- `type`
- `position`
- `config`
- `inputs`
- `outputs`
- `status`
- `created_at`
- `updated_at`
- optional `job_id` / `receipt_id`
- optional `error`

Minimum edge contract:

- `id`
- `source`
- `source_handle`
- `target`
- `target_handle`
- validation state

The client may edit position/config and request execution. It does not own provider execution state.

### Initial node families

- Product / URL / source truth
- Reference / moodboard assets
- Competitor research
- Trend / hook research
- Angle generator
- Character / continuity card
- Storyboard
- Multicut script
- Image generation
- Video generation
- QA / adversarial critic
- Compositor / finishing
- Approval gate
- Delivery / receipt
- Performance evidence / learn-again

Not every node ships in slice one. The graph contract must allow them without rewrites.

## Execution slices

### Slice 1 — First value before signup

Goal: Homepage → real no-spend plan with minimum friction.

Acceptance:

- dominant CTA starts product use rather than waitlist collection
- visitor can reach a useful plan without a paid provider call
- signup/email capture occurs after or alongside value, not instead of value
- existing spend/publish gates unchanged
- mobile path has no horizontal overflow and one dominant action

### Slice 2 — Durable executable flow graph

Goal: replace static `/studio/canvas` map with persisted editable graph foundations.

Acceptance:

- add graph persistence API/storage before enabling drag/edit affordances
- reload restores node positions/config/status
- invalid edges cannot execute
- canvas renders actual server state
- no provider call is triggered merely by dragging/editing
- existing canonical UGC factory can be represented as a default graph
- rollback can return to current static canvas

Recommended UI library: `@xyflow/react`, based on the MIT UGC-dashboard pattern, but implement against Buffer Blaster contracts rather than copying its application wholesale.

### Slice 3 — Pre-spend creative intelligence

Goal: product truth → angles → continuity → storyboard → multicut becomes visible durable artifacts.

Acceptance:

- 3–5 materially different angles
- unsupported claims are flagged
- continuity card is stored with the job/campaign
- storyboard is reviewable before generation
- provider-neutral plan generated from approved storyboard
- no paid generation during this slice

### Slice 4 — Research nodes

Goal: bring competitor/reference/trend evidence into the same graph.

Acceptance:

- sources and as-of dates retained
- research node outputs can feed angle generation
- external references are treated as structural evidence, not license to clone creative
- failures are visible and recoverable

### Slice 5 — Media adapters + receipts

Goal: approved graph artifacts route through provider-neutral generation.

Acceptance:

- provider adapter selected server-side
- estimated spend/credits shown when available
- explicit approval required
- job status appears on node
- output attaches to durable receipt
- bounded retry rules enforced

### Slice 6 — Compositor / finishing

Goal: move generated clips to campaign-ready output without leaving the product.

Minimum useful finish operations:

- trim
- sequence/stitch
- captions
- basic audio/music bed controls
- cover/frame selection
- 9:16 export first

Do not build a full nonlinear editor unless customer evidence proves it necessary.

### Slice 7 — Batch production

Goal: one approved brief can spawn controlled variations.

Acceptance:

- explicit variation dimension per child job (hook, angle, creator, format, etc.)
- cost envelope visible before batch approval
- per-job receipts/failures remain inspectable
- resume/recovery after interruption
- concurrency bounded by server policy

### Slice 8 — Evidence loop

Goal: performance evidence feeds the next round rather than ending at export.

Acceptance:

- outputs can be associated with campaign/ad identifiers
- performance imports remain traceable to source/time window
- next-angle recommendations cite actual prior evidence
- no fabricated winner language when data is absent

## ASTRA / agent training contract

ASTRA should not preload every imported repository or every provider trick. It should discover normalized umbrella skills by metadata and route work to the right procedure.

Required umbrella procedures:

1. UGC Creative Strategy
2. UGC Character Continuity
3. UGC Storyboard + Multicut
4. Provider Prompt Direction
5. UGC Adversarial QA
6. MaxFusion Gauntlet

Provider-specific volatile instructions belong in adapters/reference files, not the permanent creative doctrine.

## Gauntlet dimensions

For each dimension, compare Buffer Blaster and MaxFusion on the same user job:

- time to first useful result
- clarity of primary action
- research → concept → generation coherence
- visual flow control
- continuity/storyboard control
- generation throughput
- finishing/composition
- agent/MCP/API control
- approval/spend transparency
- evidence/learning loop
- mobile usability

Builder cannot issue the release verdict. Independent critic returns `BUFFER BLASTER`, `MAXFUSION`, or `UNVERIFIED`, with three decisive reasons.

## Current Round 0 verdict

From verified product/source inspection, MaxFusion currently has the stronger end-to-end workflow story because its public product explicitly connects competitor research, trends, ideation, image/video generation and compositor on one controllable flow canvas. Buffer Blaster is stronger on explicit pre-spend planning, approval boundaries, provider-neutral execution, and evidence receipts.

The highest-leverage gap is therefore not adding another generator. It is making Buffer Blaster's existing pieces operate as one durable, visible, executable creative graph — starting with the persisted canvas contract and pre-spend creative artifacts.

Visual superiority remains UNVERIFIED until both products are captured/rendered at matching desktop and mobile viewports and scored by a separate critic.

## Definition of done

This program is not done when code exists. It is done only when:

- the zero-friction first-value path works in production
- graph persistence/execution is real, not decorative
- research, strategy, continuity, storyboard, generation, finishing and evidence can traverse one coherent product model
- provider spend and publish remain approval-gated
- all critical paths pass existing tests plus new graph/creative tests
- desktop/mobile rendered evidence exists
- an independent critic prefers Buffer Blaster to MaxFusion on the agreed target dimensions, with any remaining losses explicitly accepted by the owner
- production has a documented rollback target
