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
