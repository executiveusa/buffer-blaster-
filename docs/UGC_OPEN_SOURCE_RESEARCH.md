# UGC open-source research — pinned pattern review

Reviewed: 2026-09-04. These repositories are reference inputs only. Buffer Blaster does not depend on them at runtime and does not import their provider credentials, billing logic, brand identity, hosted infrastructure, or model IDs.

## OpenShorts

- Repository: `mutonby/openshorts`
- Pinned revision: `3c9cc989f2d098581015a01222e79a364ee87094`
- Reviewed paths: `README.md`, `LICENSE`, clip/shorts architecture described by the project.
- License boundary: core application is MIT; the upstream `cloud/` directory is explicitly excluded from the MIT grant and uses the OpenShorts Commercial License.
- Useful patterns: self-hosted/core separation, job-oriented media processing, long-form highlight selection, vertical reframing, captions, agent-facing MCP/API, durable async work instead of browser-owned generation.
- Buffer Blaster decision: reuse the architectural pattern only. Do not copy or depend on `cloud/`; distribution/billing stays behind Buffer Blaster's own governed interfaces.

## Open-AI-UGC

- Repository: `Anil-matcha/Open-AI-UGC`
- Pinned revision: `9fffcc1a9518ea9b07ce8947891141a8aa2bf418`
- Reviewed paths: `README.md`, `LICENSE`.
- License: MIT.
- Useful patterns: one UGC workflow that switches between text-to-video and image/reference-to-video, multiple references, async job persistence, capability-aware model parameters, and generation history.
- Buffer Blaster decision: adopt the provider-neutral input/receipt shape and capability-registry idea, not the upstream provider/model list, credit rules, UI, or hosted vendor integration. Model identities remain environment-owned.

## Lazynext

- Repository: `Lazynext-Platform/Lazynext`
- Pinned revision: `e15e83128642dc8ca8bc24ed3a18eab63d4b4479`
- Reviewed path: `README.md` and documented reference-ad / UGC architecture.
- License: repository README declares MIT for the open-source project; external Atlas Cloud services remain external services and are not vendored into Buffer Blaster.
- Useful patterns: reference-ad decomposition before generation, product + presenter + reference assets as separate inputs, multi-step/multi-model orchestration behind one workflow, and duration/resolution-aware cost estimation before paid work.
- Buffer Blaster decision: strategy receipts, source provenance, provider-neutral job planning and server-owned cost ceilings. No Atlas Cloud coupling and no protected brand-identity copying.

## Adopted Phase 01 pattern

Buffer Blaster's canonical `UGCProviderJob` is deliberately smaller than any upstream application. It carries input asset references, actor/reference input, script/prompt, output format, provider/model binding, estimated cost and ceiling, approval state, idempotency key, output receipt, and failure state. Fal remains the existing first adapter. `submit_video` and `fetch_url` remain backward-compatible while `plan_job` and `submit_job` provide the neutral boundary for later routing.

## Non-adopted patterns

- no upstream authentication or billing stack
- no upstream secret handling
- no committed model IDs
- no public media bucket requirement
- no auto-spend or auto-publish behavior
- no cloud-only code with a non-permissive license
- no provider marketing claims treated as verified capability
