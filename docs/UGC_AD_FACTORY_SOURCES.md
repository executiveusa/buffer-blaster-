# UGC Ad Factory — Open-Source Sources

Buffer Blaster's UGC Ad Factory V1 reuses production patterns from open-source work while keeping the runtime provider-neutral.

## MaxFusion AI — OMNI-UGC-AD-FACTORY

- Repository: `https://github.com/MegaTroll222/OMNI-UGC-AD-FACTORY`
- License: MIT
- Copyright: Copyright (c) 2026 MaxFusion AI
- Patterns adapted in this repository:
  - structured validation before paid generation
  - two-clip continuity ordering: trim clip 1 before extracting the seed frame
  - seed clip 2 from the approved final frame of clip 1
  - seam quality assurance before stitching
  - natural-speech constraints that avoid polished direct-response closers

The MaxFusion hosted service, MCP endpoints, credentials, proprietary models, and branding are not runtime dependencies of Buffer Blaster.

This repository does not copy the upstream `references/humanizer.md` file. If that material is added later, its upstream attribution and license notice must be preserved separately.

## Existing Buffer Blaster UGC workflow

`skills/ugc-video/SKILL.md` remains a separate creative prompting source. UGC Ad Factory V1 reuses the existing provider-neutral prompt compiler and Fal media provider boundary rather than introducing another video stack.

## Prompt libraries merged 2026-09-18

Three upstream prompt libraries were merged for retrieval and benchmark use. All are ingested through `scripts/youmind_ingest.py` with provenance preserved (source repo, path, pinned commit, license, content hash); unknown-license material stays quarantined. Registries: `sources/youmind-openlab.json`, `sources/goku-openlab.json`, `sources/oside-media.json`. Compiled retrieval catalogs: `library/compiled/`. Workflow: `icm/_templates/prompt_library_run/`.

### OSideMedia/higgsfield-ai-prompt-skill

- Repository: `https://github.com/OSideMedia/higgsfield-ai-prompt-skill`
- Pinned revision: `c0b73ab946df6658cca513db78bdc3909a655bfd`
- License: MIT (LICENSE blob `bde5207152052e91eadf6162187f5d0c2e2f78e0`); LICENSE file preserved in the bolt-on copy.
- What was merged: full bolt-on copy at `skills/higgsfield/` (Seedance 2.5 references, Kling 3.0, UGC templates, identity/Soul handling, model specs, camera/motion vocabulary); 97 skill files also ingested as Agents cards for retrieval.
- What was not copied: upstream `.claude/` editor config and `.markdownlint.json`. The hosted Higgsfield platform, accounts, and credentials are not dependencies.
- Note: upstream `SKILL.md` files contain agent-facing operating rules written for the upstream project. They are reference material inside Buffer Blaster; the repository's own AGENTS.md/ICM contracts remain authoritative here.

### Goku-OpenLab/seedance-2-prompts-datasets

- Repository: `https://github.com/Goku-OpenLab/seedance-2-prompts-datasets`
- Pinned revision: `6664a7bb9ff262faf8b009c752a4997488eba7f9`
- License: CC-BY-4.0 (LICENSE blob `6bb01e935474af855c741b88603b4b90b9f4c839`)
- What was merged: `metadata.jsonl` ingested via the new `jsonl-dataset` adapter — 8,755 records in, 7,360 unique prompts after content-hash dedupe (dataset records live in the manifest/compiled catalogs, not per-card folders). Each card keeps its record id, source link, tags, category subcategory, and Hugging Face preview URL for benchmark reference videos.
- What was not copied: the 12GB+ of mp4/cover media (stays on Hugging Face; cards carry preview URLs only) and the upstream readme-render scripts.

### YouMind-OpenLab/awesome-seedance-2-prompts

- Repository: `https://github.com/YouMind-OpenLab/awesome-seedance-2-prompts`
- Pinned revision: `6f4ac511c508bcca3dbfe9f1c88ebd46557b9133`
- License: CC-BY-4.0 (LICENSE blob matches the verified sha already recorded in `sources/youmind-openlab.json`)
- What was merged: 6 featured prompts (existing numbered-readme adapter) plus 101 "All Prompts" entries via the new `titled-readme` adapter — 106 unique cards after dedupe, each with author attribution and source post link where upstream provided it.
- What was not copied: localized README translations, gallery images, and the upstream video-urls release assets (prompt text + attribution only).

### Cross-source dedupe

Exact-prompt dedupe runs per-registry at ingest and globally at compile (`scripts/build_creator_catalog.py`). 7,563 verified cards total after global dedupe; one prompt was shared verbatim between the two Seedance collections and is kept once.
