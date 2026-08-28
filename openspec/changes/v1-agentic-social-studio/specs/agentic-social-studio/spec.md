# Capability Spec — Agentic Social Studio V1

## UGC generation

Given a structured UGC brief, the system must compile a model-ready prompt in the universal order `scene -> camera -> subject -> environment -> lighting/style -> motion -> dialogue`. Provider submission must be optional and configuration-driven. Missing provider credentials must return an honest configuration error rather than a fake render.

## Publishing

The publisher interface must be provider-neutral. TryPost is the V1 default adapter. A schedule/publish request with `approved=false` must never call the upstream publisher. Successful upstream calls must return a normalized receipt including provider, external post ID/status when available, and timestamp.

## Agent operation

The same core actions must be reachable through REST, MCP, CLI, and the portable plugin skill. MCP tools must expose status, campaign planning, UGC prompt generation, social-account listing, and approved scheduling.

## Voice

Voice commands must resolve to the same explicit intents used by text commands. Scheduling/publishing intents must always be marked `requires_approval=true`. Browser speech capture may supply the transcript, but server behavior must not depend on browser speech support.

## UI

Public pages must not expose internal codenames. Product pages must provide a persistent command surface, visible approval state, and clear render/publish status. V1 must include dashboard, create, library, moodboards, canvas, calendar, campaigns, analytics, settings, landing, and pricing routes.

## Commercial packaging

V1 must present three paid tiers: Creator $39/mo, Growth $119/mo, Agency $299/mo. API/MCP/CLI access is an Agency feature in public pricing; internal operator access remains available regardless of plan during V1.
