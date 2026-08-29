# Design — UGC Ad Factory V1

## Existing seams reused
- Prompt compiler: `api/services/video_prompt.py`
- Media provider: `api/services/media_generation.py`
- REST: `api/routers/studio.py`
- Agent interface: `api/routers/mcp.py`
- ICM: `icm/_templates/*`

## New service
`api/services/ugc_factory.py`

Pure planning/validation service. It performs no network calls and selects no media model.

### Input
- product
- audience
- pain
- mechanism
- offer
- platform
- actor_description
- delivery_tone
- visual_lane

### Output
- `gate`: mechanical production checks
- `clips`: exactly two 10-second clip plans
- `continuity`: required sequence for trim → seed extraction → clip 2 → seam QA → stitch
- `icm`: stage paths an agent can walk
- `commercial`: configurable quote/cost/margin metadata
- `approval_required_before_publish: true`

## Mechanical gates
The factory must reject or avoid:
- em-dash dialogue
- direct-response closers such as buy now / shop now / link in bio / don't miss
- miracle/guaranteed claims
- scripts outside bounded per-clip word counts
- missing product, pain, or mechanism

The generated default spoken structure follows:
1. clip 1: problem + tension
2. clip 2: mechanism + complaint-as-endorsement resolution

The offer is metadata/CTA context, not forced into a salesy spoken closer.

## Continuity contract
The plan encodes ordering derived from the MIT workflow:
1. generate clip 1
2. trim clip 1 tail
3. extract final clean seed frame
4. generate clip 2 from seed
5. seam check
6. trim clip 2 tail
7. stitch

This slice does not claim FFmpeg seam automation is implemented. That is a later bounded slice after this planner is proven.

## Commercial contract
Environment-driven values:
- `UGC_FACTORY_PRICE_CENTS`
- `UGC_FACTORY_CLIP_COST_CENTS`
- `UGC_FACTORY_EXPECTED_CLIPS_PER_AD`

Defaults are estimates for quoting and must be calibrated against receipts. No checkout, Stripe, or charging behavior changes in this phase.

## Security / blast radius
No schema changes. No auth changes. No new secrets. No publishing changes. Blast radius: UGC service + studio router + MCP router.
