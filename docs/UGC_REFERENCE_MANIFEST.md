# UGC Reference Manifest

**Status:** APPROVED REFERENCE SET  
**Reference-lock date:** 2026-09-03  
**Buffer Blaster base:** `f2212aee9b3dfd56e78cd09b8054b4a3e3004fdf`  
**Purpose:** make every future UGC architecture decision traceable to an immutable upstream source before implementation begins.

This file is a provenance map, not a dependency list. A repository being listed here does **not** authorize copying its code, models, weights, training data, assets, or prompts. Before any implementation imports upstream code, the implementing agent must verify the pinned revision, code license, model/data license, NOTICE obligations, security posture, and fit with Buffer Blaster's existing architecture.

## Product law

Buffer Blaster remains the governing system. Upstreams are references for capabilities and patterns only.

Buffer Blaster owns:
- client/workspace context;
- creative intelligence and experiment intent;
- approval boundaries;
- server-owned budget controls;
- canonical receipts and provenance;
- attribution and learning;
- REST, MCP, CLI, and Studio interfaces;
- provider routing;
- optional downstream publishing.

Do not turn Buffer Blaster into a fork of any project below.

## Locked upstream references

| # | Upstream | Pinned revision | License / commercial note | Reference role | Locked inspection paths |
|---|---|---|---|---|---|
| 1 | `mutonby/openshorts` | `3e6d5c3beeb61b905e0e115dca9289e3b5682e0c` | MIT | End-to-end UGC/shorts production, actor flow, clipping, smart crop, captions, B-roll, MCP | `README.md`; `apps/web/src/actions/ugc-actions.ts`; `apps/web/src/app/api/ugc/route.ts`; `apps/workflow-core/`; `apps/renderer/`; `apps/mcp/` |
| 2 | `Anil-matcha/Open-AI-UGC` | `9fffcc1a9518ea9b07ce8947891141a8aa2bf418` | MIT | Multi-model UGC abstraction, reference-image UX, async jobs, history | `README.md`; `app/api/generate/route.ts`; `app/api/webhook/MuAPI/route.ts`; `app/api/creations/`; `components/creation-history.tsx`; `lib/muapi.ts`; `prisma/schema.prisma` |
| 3 | `Lazynext-Platform/lazynext` | `e15e83128642dc8ca8bc24ed3a18eab63d4b4479` | MIT | Reference-to-Ad, product UGC, skits, creative tools, workspace/API/MCP patterns | `README.md` at the pinned revision is the canonical feature reference. Exact implementation path for Reference-to-Ad must be resolved and recorded before any code reuse; do not infer it from a filename. |
| 4 | `poptechstudio/ai-cinema-studio-engine` | `658330970fe28b104333642dcc390466ad294eb9` | MIT | Premium finishing, cinematography RAG, multi-shot production SOP, Remotion/FFmpeg, human gates | `README.md`; follow its documented orchestration, virtual-production/RAG, post-production, and MCP skill paths only after path verification at this SHA. |
| 5 | `HarderSoftware/HeyGem.ai` | `ef768718c1db70c31f4632768f5cadf450f5f355` | **Custom commercial terms**; not unrestricted MIT. Commercial agreement threshold applies per upstream terms. | Sovereign digital-human cloning/voice/lip-sync candidate | `README.md`; upstream license/terms at the pinned revision; Docker/API entrypoints documented there. **No integration until license and consent review passes.** |
| 6 | `Omni-Avatar/OmniAvatar` | `1536bf31abaec74364fb7d5883470d5b23ffa7f8` | Apache-2.0 | Audio-driven avatar with body motion; local-provider R&D candidate | `README.md`; `LICENSE.txt`; implementation/config paths referenced by the pinned README. |
| 7 | `antgroup/echomimic_v2` | `38c86809efa041884c774ee31d984a9577c0e0aa` | Apache-2.0 | Semi-body audio-driven avatar baseline; compatibility reference | `README.md`; Apache license; Gradio/ComfyUI/inference paths linked from pinned README. |
| 8 | `antgroup/echomimic_v3` | `7e89489ca51c0d008fc1963ec6c03fc5bd0b9397` | Apache-2.0 | Preferred EchoMimic sovereign avatar candidate; faster/lower-VRAM 2026 path | `README.md`; inference/config paths documented by pinned README. Prefer V3 over V2 for new R&D unless a compatibility reason is recorded. |
| 9 | `KlingAIResearch/LivePortrait` | `9b294b3d0536135442ea73cb01e6cb3ca7029dd3` | Code MIT; bundled **InsightFace models are non-commercial**. | Efficient portrait animation / retargeting primitive | `README.md`; `LICENSE`; commercial deployment must replace/remove restricted InsightFace model assets before approval. |
| 10 | `Anil-matcha/AI-Youtube-Shorts-Generator` | `687599cd413d91a16b2b11bca0d06371253ea5cf` | MIT per upstream README | Long-form-to-short repurposing, transcription, highlight/virality scoring, smart crop | `README.md`; implementation paths described there for yt-dlp, faster-whisper, OpenCV/FFmpeg, highlight ranking and JSON output. |
| 11 | `harry0703/MoneyPrinterTurbo` | `e77ae83f697d92eae71c6503cf010733ce060b67` | MIT | Deterministic batch-video assembly and API/WebUI patterns | `README.md`; `LICENSE`; script/media/subtitle/music/video assembly paths documented at pinned revision. |
| 12 | `mohithkotian/UGC-ads` | `27d0cc13f37afec50e628d933843ffa52e29bd75` | MIT per upstream README | Product-image + creator/model-image composition flow | `README.md`; React/Vite + Express/Prisma + Vertex/Cloudinary/FFmpeg architecture documented there. Use as a small lifecycle reference, not a core dependency. |
| 13 | `backblaze-b2-samples/ai-avatar-video-generator` | `e9f82d306e7d5e0e98822dc14c1fceb29124b68e` | MIT per upstream README | Provider abstraction, per-project manifests, multiple takes, agent-first repo discipline | `README.md`; `AGENTS.md` when present at pinned revision; project manifest/storage/provider adapter paths referenced by upstream docs. |
| 14 | `SamurAIGPT/Generative-Media-Skills` | `cab141cccc7468c18e0bc6ce6a76ebcc5c853b9a` | MIT | Agent-native media skill/recipe contracts, MCP and CLI ergonomics | `README.md`; `core/`; `library/`; workflow/recipe paths at pinned revision. Adopt the contract pattern, not provider lock-in. |
| 15 | `SamurAIGPT/Vibe-Workflow` | `f433dd5f94795908f7ab6c5b3e7185754497de55` | MIT per upstream README | Expert-mode node/workflow builder reference only | `README.md`; Next.js/FastAPI workflow architecture documented there. **Do not add a node editor to the default Buffer Blaster UI without a separate approved product decision.** |

## Provenance rules

Every implementation PR influenced by this manifest must state:

1. **Capability:** what Buffer Blaster capability is changing.
2. **Reference:** upstream repo + pinned SHA + exact source path(s) actually inspected.
3. **Adoption type:** `concept`, `interface-pattern`, `algorithm`, `code`, or `model`.
4. **License result:** code license and, when applicable, model/data license.
5. **What was not copied:** explicitly identify excluded provider lock-in, billing layer, UI, model weights, or restricted assets.
6. **Buffer Blaster owner:** where the canonical result/receipt lives after integration.
7. **Human gate:** what approval still protects spend, publishing, cloning, or destructive behavior.

If code is copied or adapted, preserve notices/attribution required by the upstream license. If the agent cannot establish the license of the exact file or model, it must stop and treat that material as reference-only.

## Capability provenance map

| Buffer Blaster capability | Primary references | Secondary references | Buffer Blaster invariant |
|---|---|---|---|
| Reference-ad intelligence | Lazynext | OpenShorts, AI YouTube Shorts Generator | Extract strategy/structure; do not reproduce protected expression pixel-for-pixel or script-for-script. |
| Multi-reference UGC generation | Open-AI-UGC | UGC.AI, OpenShorts | One normalized request/receipt model; provider details stay behind adapters. |
| Creator/avatar takes | Backblaze avatar generator | OpenShorts, HeyGem, OmniAvatar, EchoMimic, LivePortrait | Multiple takes preserve lineage, consent, model/provider, cost, and artifact hash. |
| Hosted rendering | Existing Buffer Blaster Fal path | Open-AI-UGC | Fal remains a provider, never the data/provenance authority. |
| Sovereign/local avatar rendering | EchoMimic V3 | OmniAvatar, LivePortrait, HeyGem | Optional provider capability; never required for the core product to function. |
| Long-form repurposing | AI YouTube Shorts Generator | OpenShorts | Source transcript and source-media lineage stay attached to every derived clip. |
| Editing / captions / B-roll | OpenShorts | MoneyPrinterTurbo | Deterministic assembly with reproducible parameters and artifact receipts. |
| Premium/cinematic finish | AI Cinema Studio Engine | Generative Media Skills | User selects a finish mode; premium treatment must not overwrite raw UGC authenticity by default. |
| Agent skill layer | Generative Media Skills | OpenShorts MCP, Lazynext MCP | REST/MCP/CLI all route through the same server-side approval and budget controls. |
| Expert workflow UI | Vibe Workflow | AI Cinema Studio Engine | Reference-only until proven need; default Studio stays simple. |

## Commercial / trust hard stops

- **HeyGem:** do not integrate or redistribute until its exact commercial terms at the pinned revision are reviewed for the intended client deployment.
- **LivePortrait:** do not ship bundled InsightFace detection/model assets in a commercial Buffer Blaster deployment. Replace them with a commercially permitted detection stack or keep LivePortrait out of that deployment.
- **Voice/face cloning:** require explicit rights/consent evidence before generation; never infer permission from a public image/video.
- **Reference ads:** analyze hooks, pacing, structure, shot logic, proof devices and CTA mechanics; do not create deceptive replicas of a competitor's protected creative.
- **Models:** a permissive repository license does not imply permissive weights, datasets, or provider terms.
- **Client data:** private by default. Do not send a client's proprietary assets to a provider that has not been enabled for that workspace.
- **Secrets:** server-side only. No provider secret belongs in `NEXT_PUBLIC_*`, client bundles, prompt receipts, or logs.
- **Money:** existing server-owned budget wallet and approval gates remain authoritative for every hosted or local generation path.

## Upgrade rule

These revisions are intentionally immutable. A future upstream update is **not** automatically adopted. To move a pin:
1. open a dedicated reference-update PR;
2. compare the old and new revisions;
3. re-check license/model terms;
4. record new relevant paths/capabilities;
5. run the ICM Walk Test;
6. merge only after review.

This prevents an upstream `main` branch from silently changing Buffer Blaster's architecture or legal posture.
