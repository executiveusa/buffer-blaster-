# Lessons learned: Jalen UGC renders (Nov 2026)

What we learned making the Postatees car ad and the two NO IDOL NO RIVAL promos. Prices are Fal list
prices at the time and will drift; check before quoting.

## Money

- **Veo 3.1 is the priciest model we used.** Fast is $0.15/s with audio, standard is $0.40/s with audio
  (4, 6 or 8 s clips). Use it only for the hero shot that needs real physics, nothing else.
- **Cut the count, not the quality.** Going from 4 statues to 2 took the v2 plan from $4.88 (Fast) /
  $8.88 (Premium) down to $3.11, and the edit still felt full by holding about 4 s on each crumble.
- **Final v2 spend was $3.71 of the $4.00 cap**, which included one Veo retake of statue 1. Always keep
  room in the cap for one retake of each physics shot.
- **Approve a still before paying for motion.** A $0.04 (Nano Banana) or $0.15 (Nano Banana Pro) first frame
  catches bad staging before a $0.60 to $2.40 video call.
- Voice-locked Kling v3 Pro costs $0.196/s instead of $0.168/s (10 s: ~$1.96 vs ~$1.68). Worth it: an
  unlocked voice changed between takes in the car ad.
- Quote the price and get Bambu's yes before every paid run.

## What the models actually did

- **Statue 1, take one rebuilt itself after breaking.** Veo 3.1 Fast exploded the statue and then it
  reformed. We paid for a retake (`v2-raw/vid_s1b.mp4`). Veo tends to leave statues standing or reforming.
  Fix in the edit: cut right before the reform and slow-mo the break.
- **Statue 2 breaks to dust but does not fully topple.** It reads fine in the cut. A full topple would have
  needed another take, roughly **$0.60 more**; we kept the money.
- Prompting "collapses", "falls over" is not enough. Expect partial destruction and plan the cut around it.
- AI scrambles lettering every time (sleeve text, POSTA TEES print). Use real product photos for any logo
  close-up, and keep sleeves out of frame.
- Kling v3 Pro on Fal is 1080p-only and needs `generate_audio` set; it ignores a 720p/silent request.
- The two car-ad takes came out as two different voices (~114 Hz vs ~156 Hz). Locking the Kling voice id fixed it.

## Look

- **Modern means no fisheye.** v1 used the late-90s hip-hop video look (fisheye, chrome type, strobes); for
  the 16 to 30 audience Bambu wanted v2 modern: smooth motion-control moves, anamorphic shallow focus, one hard
  gold top light on black, haze, macro texture, clean small type. No fisheye, no chrome, no strobes.
- Faceless marble statues wearing hype symbols (crowns, chains, trophies) keep "idols" anonymous: no real
  person's likeness.
- Keep the whole car ad in the car; no stitches to bleachers or other locations.

## Cheaper options to try next (discussed, not yet tested)

- **Kling, LTX or Wan for the non-hero shots** (walks, macros, wides). Save Veo for the one physics shot.
  Kling 2.5 Turbo Pro is $0.35 per 5 s and did fine on the walk and macro shots.
- **GPU rental** to run open models (Wan, LTX) by the hour instead of paying per clip, once volume justifies it.
- **Muapi**: claimed to be cheaper, **unverified**. Do a small priced test before trusting it.
- ACE-Step on Fal is basically free for beats ($0.0002/s, a 30 s take is about $0.01).

## Process

- Fal keys are pasted one time in chat, never written to a file or repo, and revoked after each run.
- Motion Master (HyperFrames) renders the title and end cards for free; see motionmaster PR #16.
- For ffmpeg stills use `-framerate 30 -loop 1 ... -frames:v N` (the 25 fps default breaks beat timing).
