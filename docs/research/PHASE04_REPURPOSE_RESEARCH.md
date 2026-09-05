# Phase 04 — Long-form repurpose research boundaries

Phase 04 studies long-form-to-short-form workflow patterns without importing an external product runtime, model, provider credential, or billing path.

## Patterns reviewed

### AI-Youtube-Shorts-Generator
Useful pattern: transcript-backed highlight selection followed by vertical short-form preparation. Buffer Blaster does not import its runtime, provider configuration, or model assumptions.

### OpenShorts
Useful patterns: long-form ingestion, ranked moment planning, vertical 9:16 crop intent, captions, batch processing, and agent/API-oriented control. Buffer Blaster does not make OpenShorts a runtime dependency and does not copy its provider or billing ownership.

## Buffer Blaster implementation

The Phase 04 implementation remains provider-neutral and deterministic:

1. caller supplies an owned/private source asset key plus transcript segments;
2. transparent heuristics rank hook/proof/action/specificity moments;
3. overlapping windows are suppressed to diversify the batch;
4. each selected clip receives source timestamps, mobile crop intent, caption lines, b-roll guidance and finish guidance;
5. the result is persisted as an existing canonical `creative_jobs` receipt with kind `repurpose_plan`;
6. repeated idempotency keys replay the same receipt and conflicting payloads fail closed;
7. planning records zero estimated provider cost and never calls a transcription, generation or publishing provider.

## Explicit non-goals

- no automatic transcription provider in this phase;
- no paid highlight-detection model;
- no renderer invocation;
- no social scheduling clone;
- no provider/model key or model ID in the client contract;
- no new database table where the canonical creative-job ledger already fits.

Rendering the resulting plans remains a separate consequential action behind the existing approval and wallet controls.
