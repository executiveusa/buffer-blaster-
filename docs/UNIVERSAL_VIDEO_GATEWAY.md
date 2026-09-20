# Universal Video Gateway — research and integration notes

Reviewed: 2026-09-19.

## Goal

Let Buffer Blaster keep one governed UGC/video execution contract while routing an approved render to different model catalogs without hard-coding model families into business logic.

The implementation in this branch keeps:

- provider credentials server-side;
- an explicit model allowlist;
- human approval before paid generation;
- the existing wallet/spend boundary;
- provider/model provenance in receipts;
- Fal as the default rollback path.

## Open-source references reviewed

### Autom8AI/Open-Higgsfield-AI

- MIT licensed.
- Self-hosted creative UI with 200+ image/video/lipsync model definitions.
- Uses MuAPI as the runtime gateway.
- Submit/poll pattern: model endpoint -> prediction result endpoint.
- Useful pattern: one model catalog plus dynamic capability-aware controls.
- Reused here as architecture inspiration only; Buffer Blaster does not import its UI or API key storage.

### samagra14/mediagateway (MediaRouter)

- MIT licensed open-source video generation gateway.
- OpenAI-compatible API surface.
- BYOK, cost tracking, self-hosting, multi-provider routing.
- Useful as a candidate sovereign gateway behind Buffer Blaster's new adapter.

### AngeVox/AngeMedia-gateway

- Self-hosted OpenAI-compatible image/video gateway.
- Provides async video jobs and provider/model routing.
- Useful as another drop-in gateway candidate.

### yolorouter/yolorouter

- Self-hosted OpenAI-compatible gateway.
- Includes video jobs and native media adapters including Volcengine Ark / Seedance, Kling, MiniMax and Wan-family paths.
- Useful for direct/provider-level routing when operator-owned keys are preferred.

### calesthio/OpenMontage

- Agentic open-source production system with many provider adapters.
- Includes direct and gateway-backed video paths such as Kling, Seedance, MiniMax, Veo and local models.
- Useful as a provider-adapter and orchestration reference; Buffer Blaster remains the product/runtime.

### gateway/media-studio

- Open-source image/video studio over a KIE API layer.
- Current model surface includes Seedance 2.5, Kling 3.0 and other media models.
- Useful as evidence that Seedance 2.5 can be exposed behind a catalog-driven async gateway.

### ai-models-lab/seedance-2.5

- Multi-provider Seedance 2.5 tooling.
- Documents Volcengine Ark, Fal and Replicate paths.
- Useful for provider-specific Seedance experiments, not as Buffer Blaster's core abstraction.

## Architecture decision

Do not fork another studio into Buffer Blaster.

Use a **universal async gateway boundary**:

```
Buffer Blaster UGC factory
        |
        v
approval + wallet + cost guard
        |
        v
UniversalVideoGatewayProvider
        |
        +--> self-hosted MediaRouter / AngeMedia / YoloRouter
        +--> MuAPI (Open-Higgsfield style)
        +--> other compatible async gateways
        +--> direct provider gateway we control later
```

The adapter supports:

- configurable base URL;
- configurable auth header/prefix;
- configurable submit path with `{model}`;
- configurable status path with `{id}`;
- GET or POST polling;
- model in request body on/off;
- text-video and image-video model defaults;
- server allowlist for arbitrary model IDs;
- optional per-job model selection carried through the existing factory request.

## Seedance 2.5

Buffer Blaster does not hard-code Seedance 2.5.

To enable it, the operator configures a gateway that actually exposes the model and adds its exact gateway model ID to `GENERATION_GATEWAY_ALLOWED_MODELS`.

Example for a MuAPI/Open-Higgsfield-shaped gateway:

```env
ACTIVE_MEDIA_PROVIDER=gateway
GENERATION_GATEWAY_NAME=muapi
GENERATION_GATEWAY_BASE_URL=https://api.muapi.ai
GENERATION_GATEWAY_AUTH_HEADER=x-api-key
GENERATION_GATEWAY_AUTH_PREFIX=
GENERATION_GATEWAY_SUBMIT_PATH=/api/v1/{model}
GENERATION_GATEWAY_STATUS_PATH=/api/v1/predictions/{id}/result
GENERATION_GATEWAY_MODEL_IN_BODY=false
GENERATION_GATEWAY_TEXT_VIDEO_MODEL=seedance-2.5
GENERATION_GATEWAY_IMAGE_VIDEO_MODEL=seedance-2.5
GENERATION_GATEWAY_ALLOWED_MODELS=seedance-2.5
```

The exact model ID and commercial terms must be verified against the chosen provider at runtime.

## Why this instead of importing Open-Higgsfield wholesale

Buffer Blaster already has:

- UGC planning;
- receipts;
- cost ceilings;
- approval boundaries;
- storage;
- stitching/QA;
- REST/MCP/CLI surfaces;
- provider routing.

Importing another studio would duplicate the product and create two sources of truth. The useful part is the **catalog/gateway pattern**, not the second UI.

## Rollback

Set:

```env
ACTIVE_MEDIA_PROVIDER=fal
```

and keep the current Fal variables. No schema migration is introduced by this slice.
