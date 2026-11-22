# Jalen: UGC character kit

Everything made with **Jalen**, the house-cast UGC character for Postatees ads: who he is, how to
render him, every video, still and voice sample so far, the scripts, the costs, and what we learned.
Jalen is AI-generated, not a real person, so there is no likeness release to chase.

Read [`lessons.md`](lessons.md) before spending money on the next render.

## Quick facts

| | |
|---|---|
| Character id | `jalen` |
| Bible (look, wardrobe, voice, pronunciation, prompt block) | [`character/BIBLE.md`](character/BIBLE.md) |
| Locked voice | Fal Kling voice id **`952742773105512039`** (cloned 2026-11-21 from `character/voice-clone-source.mp3`, $0.007) |
| How to use the voice | Kling v3 `elements[].voice_id = "952742773105512039"`, and call him `@Element1` in the prompt |
| Main first frame | `character/ref-hero-hood-down.jpg` (720p, from the car ad) |
| Brand | Postatees, said **POH-stuh-teez**. Write `Poh-stuh-teez` in spoken lines, real spelling in captions |

The voice id is a public identifier for a voice on Bambu's Fal account, not a secret.
**No API keys are stored anywhere in this folder.** Fal keys are given one time per run and revoked after.

## What is in here

```
character/            BIBLE.md, 3 reference stills (jpg 720p + png), voice samples
  voice-clone-source.mp3   take 1 only, 7.3 s: the source of the locked voice
  voice-sample-full.mp3    both takes from the car ad, for listening
  voice-take1-hook.wav     the keeper read (~114 Hz, low and laid back)
  voice-take2-shoutout.wav the off-voice read (~156 Hz, brighter): do not copy

postatees-car-ad/     Ad 1: Postatees x Mariner Marauder hoodie, all in the car
  final/postatees-mariner-car-ad.mp4       the finished ad
  buffer-blaster/first-frame*.png          Nano Banana edit keyframes
  buffer-blaster/fal-test-render-old-frame.mp4  first Fal test render
  refs/hoodie-mockup.jpeg                  product reference

no-idol-promo/        Ad 2: "NO IDOL NO RIVAL" Postatees Puffer promo ($240 jacket)
  PLAN.md, STYLE.md                        v1 plan and late-90s look book
  SCRIPT-v2.md                             v2 "The Idols Fall" script, shot list, prompts, costs
  no-idol-no-rival-puffer-promo-v1.mp4     v1 final (17.5 s, retro hip-hop look)
  no-idol-v2-the-idols-fall.mp4            v2 final (17 s, modern, 2 statues)
  clip_a..d.mp4, still_a..d.jpg            v1 Kling clips and their first frames
  intro-v2.mp4, title-slam.mp4, end-card.mp4, v2-title-draft.mp4   Motion Master type
  no-idol-animatic-v1.mp4                  animatic with stand-ins
  beat-original.wav                        original ACE-Step beat
  refs/puffer-*.jpg|png                    real product photos (use these for logo close-ups)
  v2-raw/                                  v2 raw generations: statue frames (f_s1, f_s2), Veo clips
                                           (vid_s1 first take, vid_s1b retake, vid_s2), wide (vid_w),
                                           macro (vid_m), close-up (vid_c), beat1.wav
```

## Spend so far

| Piece | Models | Cost |
|---|---|---|
| Car ad keyframe + clip | Nano Banana edit $0.04, Kling v3 Pro i2v 10 s with audio ~$1.40 | ~$1.44 |
| Voice clone | `fal-ai/kling-video/create-voice` | $0.007 |
| No Idol v1 | 4 Nano Banana stills, 3 Kling 2.5 Turbo clips, 2 ACE-Step beats, 1 Kling v3 Pro 5 s voiced | ~$2.20 (cap $2.50) |
| No Idol v2 | Nano Banana Pro statue frames, Veo 3.1 Fast statue crumbles (+1 retake), Kling 2.5 Turbo, Kling v3 voiced close-up, ACE-Step | **$3.71** (quoted $3.11, cap $4.00) |

Title and end-card compositions live in the motionmaster repo (`generator/compositions/no-idol*`, PR #16).
The Montage and Buffer Blaster app wiring for Jalen is in Montage PR #12 and Buffer Blaster PR #124.

## Storage

Videos, audio and PNGs in this folder are stored with **Git LFS** (see the repo's `.gitattributes`).
Run `git lfs install` once, then `git lfs pull` to get the real files after cloning.
