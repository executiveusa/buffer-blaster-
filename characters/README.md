# House cast

Locked characters any ad can reuse. Put `"character": "<id>"` on a UGC brief
(REST `/api/studio/ugc/factory/plan|execute`, MCP `create_ugc_ad_factory_plan`,
or `python -m cli.render_local`) and the planner fills in the actor, setting,
voice description, delivery and pronunciation from `characters/<id>/character.json`.
`GET /api/studio/characters` and `python -m cli.render_local characters` list them.

| Id | Who | Voice locked on a provider? |
|---|---|---|
| `jalen` | Young Black man in the deep navy Postatees x Mariner hoodie, driver's seat of a parked car. See [jalen/BIBLE.md](jalen/BIBLE.md). | Yes: Fal Kling voice `952742773105512039` (saved 2026-11-21) |

## What a character folder holds

- `character.json`: prompt text for look, setting, delivery, voice; pronunciation; things to avoid; reference and voice file names.
- `refs/`: reference stills. The first (`references.frontal`) is the main face reference.
- `voice/clone-source.mp3`: 5 to 30 s of clean, single-voice audio for a voice clone.
- `BIBLE.md`: the human-readable character bible.

## Locking the voice (one paid call)

`python -m cli.render_local voice-create jalen --approve-cents 1` saves the
voice on Fal (`fal-ai/kling-video/create-voice`, **$0.007**) and prints a
`voice_id`. Put it in `character.json` under `voice.kling_voice_id`, or export
`CHARACTER_JALEN_KLING_VOICE_ID`. From then on every render of a Jalen brief
sends Kling v3 `elements` (his face references plus the saved voice) and the
prompt calls him `@Element1`.

Voice-controlled Kling v3 Pro clips cost **$0.196/s** instead of $0.168/s
(10 s: about $1.96 instead of $1.68). Set `FAL_ESTIMATED_CLIP_COST_CENTS=196`
for 10 s voice-locked renders.

Keyframes: `python -m cli.render_local keyframe BRIEF.json --reference hoodie.jpg --out frame.png --approve-cents 4`
puts the character's photos first, so the first frame is the same man.
