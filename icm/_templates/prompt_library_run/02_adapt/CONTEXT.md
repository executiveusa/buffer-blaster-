# 02 Adapt

## Job
Adapt exactly one shortlisted prompt to the brief without erasing provenance.

## Process
1. Open the chosen card's full prompt from `library/compiled/full-cards.json`.
2. Apply the Higgsfield skill structure when the target is a Higgsfield/Seedance model: read `skills/higgsfield/SKILL.md` and route to `skills/higgsfield/skills/higgsfield-seedance/SKILL.md` for Seedance 2.5 work (block-scaffold prompts, camera/motion vocabulary, model specs in `skills/higgsfield/specs/`).
3. Swap in the brief's product, audience, tone, and platform. Keep the structural bones that made the reference prompt work (shot timing, camera moves, consistency constraints).
4. Keep the prompt inside the target model's regime (single-shot MCSLA soft cap ~200 words; block-scaffold production prompts follow the Seedance sub-skill's structural lint instead).

## Output
`output/adapted-prompt.md` — the adapted prompt plus a provenance header: source repo, source path, content hash, license, adapter, and a one-line note of what was changed.
