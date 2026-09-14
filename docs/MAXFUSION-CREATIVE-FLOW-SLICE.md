# MaxFusion Creative Flow Slice — Brownfield Spec

Status: SPEC LOCK — implementation must stay on `feat/maxfusion-creative-flow` until proof passes.
Classification: SELL (revenue offer)
Benchmark: MaxFusion behavior/outcome bar, not a design/code clone.

## Outcome
Turn Buffer Blaster's existing honest but mostly static Canvas + persisted Moodboards into a usable zero-friction creative workspace where a visitor can move from reference/product truth to angle, script, shot plan, approval and real job receipt without creating a second source of truth.

## Baseline
### What already works
- `/studio/create` has a real no-provider-spend planning gate before paid media generation.
- `/studio/moodboards` persists canonical reference assets from URL/upload.
- `/studio/canvas` truthfully maps the executable factory and links to real Moodboards/Create flows.
- Generation/publish actions remain approval gated.

### Current weakness
The Canvas explicitly locks node editing. It is a diagram, not a working creative surface. Moodboards persist assets but render them as a simple grid, with no spatial clustering, relationship to angles/scripts, or drag-to-flow interaction. This is the highest-value UX gap to close before adding more disconnected features.

## Product rule
Do not build a generic whiteboard.
Build the smallest executable creative graph whose nodes correspond to real Buffer Blaster entities and whose actions call existing workflows.

## Canonical graph
Typed nodes only:

1. `reference` — persisted `ReferenceAsset`
2. `product_truth` — product, audience, customer pain, mechanism, offer, platform
3. `angle` — testable creative angle/hook
4. `script` — approved/bounded script or multicut plan
5. `shot` — shot/camera/character continuity instruction
6. `generation_plan` — provider route + expected cost/credit requirement
7. `asset` — generated/stored output with durable job receipt
8. `approval` — human decision boundary
9. `evidence` — performance/QA result used by next iteration

Every node must either persist to an existing canonical model or have an explicitly specified new persistence contract before it becomes editable.

## First verifiable slice
### Desktop
- Replace the static four-column Canvas diagram with draggable typed cards on a constrained canvas.
- Existing saved Moodboard references appear in a reference tray.
- Dragging a reference onto the canvas creates a graph reference node backed by its existing reference ID.
- A `product_truth` node can be created from the same fields already used by `/studio/create`.
- `Build plan` invokes the existing no-spend planning path; it must not call a paid media model.
- The returned angle/script/generation-plan data becomes real downstream nodes.
- Paid generation remains an explicit gated action from the generation-plan node.
- Finished output links to the real job receipt/library entry.

### Mobile
Do not force free-form drag behavior onto a narrow screen.
- Render the same graph as an ordered card stack/timeline.
- Reorder with explicit Move Up/Move Down or accessible drag handles only if reliable.
- Keep one dominant action visible: Continue / Build plan / Review / Approve, depending on state.
- Zero horizontal page overflow.

## Moodboard upgrade
Keep Moodboards as the canonical source-asset library, but add:
- real image thumbnails when available
- labels/tags
- select/multi-select
- `Add to Flow` action
- optional spatial grouping on desktop only after persistence exists

Do not duplicate asset storage inside Canvas.

## Source mining / reuse boundaries
### `harshith-vaddiparthy/UGC-dashboard`
Use as an interaction/reference source after license verification. Mine:
- workflow layout patterns
- UGC asset organization
- campaign/creative hierarchy
- useful information density
Do not wholesale transplant its UI or data model.

### `joebenscoter86/higgsfield-ugc-workflow`
MIT verified. Adapt procedure concepts with attribution/provenance:
- product profile
- UGC brief
- base character / continuity
- storyboard sheet
- multicut script
- UGC ad/video/enhancement stages

### `AKCodez/higgsfield-claude-skills`
No license found during intake. Concepts only. Useful areas include e-commerce hooks, social hooks, brand story, cinematic/camera language and product-showcase thinking. All Buffer Blaster implementation/copy must be independently written.

### MaxFusion
Use as adversarial product benchmark for:
- speed to first value
- workflow coherence
- visual hierarchy
- directness of actions
- evidence that one workspace replaces tool-hopping
Do not copy proprietary layout, wording, media or source.

## Skill integration seam
Buffer Blaster should consume creative procedure outputs through its existing plan/provider contracts rather than embedding a provider-specific prompt library in the UI.

Expected procedure outputs:
- angle candidates
- hook type
- character/continuity card
- beat sheet / storyboard
- multicut script
- shot/camera direction
- provider-neutral generation plan
- independent QA verdict

Provider adapters translate the approved plan to Fal/Higgsfield/other media providers. The product-level graph stays provider-neutral.

## Gauntlet
Use the uploaded gauntlet-loop method as the release gate.

Each round:
1. Render Buffer Blaster challenger and MaxFusion reference at the same desktop viewport.
2. Render both at the same mobile viewport.
3. Builder critiques only the challenger.
4. Separate critic compares reference vs challenger without being told which to favor.
5. Critic returns binary `REFERENCE` or `CHALLENGER` plus the three highest-impact mismatches.
6. Fix only those mismatches plus any broken interaction/accessibility defect.
7. Re-run functional tests and repeat.

Default: 4 rounds. Continue only while there is measurable improvement and no architecture/governance regression.

### Scored dimensions
- pain clarity / promise
- time to first useful output
- product demonstration
- hierarchy / information density
- interaction confidence
- reference → idea → plan flow
- mobile usability
- trust / cost visibility
- accessibility
- factual claim integrity

### Pass bar
- Overall >= 8.5/10
- Conversion / first-value path >= 9/10
- No P0/P1 interaction failures
- No horizontal mobile overflow
- No fake/dead control
- No provider spend before explicit approved stage
- Independent critic selects `CHALLENGER` in the final two consecutive rounds, OR a documented blocker explains why comparison cannot be completed.

## Tests
- reference tray loads only persisted canonical assets
- add-to-flow preserves reference IDs
- graph reload preserves nodes/edges
- build-plan path is provider-spend free
- generation remains gated
- invalid/orphan node IDs fail visibly
- mobile ordered representation has the same semantic workflow as desktop
- keyboard path can reach/select/move nodes and execute primary actions
- existing REST/MCP/UI parity remains intact

## Definition of done
A new visitor can open Buffer Blaster, provide product truth or a reference, get a useful no-spend creative plan, see that plan become a visual flow, and understand exactly what happens/costs before approving generation. The same run produces durable canonical records and can be resumed. Mobile is a first-class ordered workflow, not a shrunken desktop canvas. Final release requires gauntlet evidence and human approval.

## Rollback
- Preserve current Canvas and Moodboard route implementations in Git history.
- New graph persistence must be additive/migrated with a reversible migration.
- If the interactive graph fails production proof, route Canvas back to the current truthful static map without affecting `/studio/create`, canonical references, generation, or job receipts.