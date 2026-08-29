# Design — Launch Proof V1

## Positioning contract
Public promise: **Find the angle. Make the ad. Prove what works.**

Support: Social Studio turns product truth into research-grounded UGC production: brief → script gate → render → review receipt. Agents can call the same flow through MCP.

Do not claim "winning ads" before customer performance evidence exists.

## Offer contract
**Founding Ad Batch — $249**
- 3 vertical UGC ads
- 3 distinct pain/angle hypotheses
- 9:16, review-ready files
- approved scripts/production prompts retained with the batch
- one revision round
- generation/QA receipts retained

This is launch positioning, not automated customer billing. Payment wiring is a separate human-approved change.

## UI contract
Replace prompt-first Create UX with five human inputs:
1. Product
2. Audience
3. Customer pain
4. Product mechanism
5. Offer

Primary action: `Build batch plan`.

Plan output must show:
- mechanical gate pass/fail
- clip scripts and word counts
- six ICM stages
- quote metadata
- approval state

A secondary action `Approve & render clip 1` is enabled only after a plan passes. That click is the explicit paid-generation approval.

## Execution contract
Add one service helper that:
1. builds the deterministic factory plan
2. refuses generation when the plan gate fails
3. refuses generation unless `approved` is true
4. selects clip 1 or 2 from the plan
5. submits the plan's compiled prompt verbatim through `get_media_provider().submit_video`
6. returns provider request/status/response URLs plus the plan/clip identity

No model IDs are selected in this service.

## Agent contract
MCP adds `render_ugc_ad_factory_clip` with required product/audience/pain/mechanism and `approved` boolean. Unapproved calls return a structured error without contacting Fal.

## Trust contract
The product surface distinguishes:
- PLANNED
- GATE PASSED
- APPROVED TO SPEND
- RENDER QUEUED
- REVIEWED
- PUBLISHED

A queued render is never represented as a finished ad.

## Proven–Better–New application
### Proven — copy
- end-to-end workspace instead of tool hopping
- visual production flow
- agent/MCP access
- model/provider abstraction
- research before generation
- clear output economics
- visible proof/examples

### Better — emphasize
- price/output in finished-ad language rather than opaque credits
- research truth and mechanical gates before paid calls
- provider receipts and approval trail
- owner-controlled ICM/exportability
- any-agent cold-walk contract

### New — quarantine
- ICM portability across agent runtimes
- machine-readable proof/approval ledger
- future performance-learning loop

None of these new elements may be required for basic plan → render operation.