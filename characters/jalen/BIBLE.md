# Jalen: character bible

Working name: **Jalen** (rename any time; the id `jalen` is what code uses).
First seen: the Postatees x Mariner car ad, 2026-11-21 (`postatees-ad/final/postatees-mariner-car-ad.mp4`).
He is an AI-generated person, not a real individual, so there is no likeness release to chase.

## 1. Look (lock these, every render)

- Young Black man, 18 to 20, warm medium-brown skin.
- Short dark curly/coily hair on top, tight taper on the sides. Thin mustache with a light chin-strap beard.
- Dark brown eyes, slim athletic build, easy wide smile with straight white teeth.
- Expression range: relaxed half-smirk at rest, big open grin on the payoff line. Never stern.

## 2. Wardrobe

- **Deep navy** pullover hoodie (the first render drifted to royal blue: always say "deep navy").
- Gold oval chest badge with the orca and POSTATEES wordmark, left chest, embroidered.
- Black drawstrings, plain dark grey tee under the hood.
- **Chest-up framing only.** No sleeve close-ups: AI cannot spell the sleeve lettering.
- Two looks: **hood down** (hero, daytime or dome light) and **hood up** (night, rain, stadium lights).

## 3. Setting

- Driver's seat of a parked car, phone selfie at arm's length, slight handheld drift.
- Default: night, parked beside a high school football field under floodlights, rain beads on the windows, warm dome light on his face.
- Daytime variant: overcast Everett daylight through the windshield.
- No stitches to other locations: the whole ad stays in the car.

## 4. Reference images

| File | Use |
|---|---|
| `ref-hero-hood-down.jpg` | **Main reference / first frame.** Neutral half-smile, badge visible, no captions. |
| `ref-smile-hood-down.jpg` | Second angle: big grin, slight head turn. |
| `ref-hood-up-face.jpg` | Night hood-up look, face crop (the ad's captions sat lower, so this is cropped above them). |

All three are 720p stills pulled from the final ad. Good enough as identity references; for a crisp 1080p hero still see "Upgrades" below.

## 5. Voice

What the first ad had (measured from the audio): two different takes that do **not** match.
- Take 1, the hook ("Everett don't get collabs... Embroidered. Not printed."): low and laid-back, median pitch about **114 Hz**, slow with punchy pauses (~1.3 words a second). This is the keeper.
- Take 2, the shout-out: brighter and higher, median about **156 Hz**, ~2.5 words a second. Sounds like a different, younger guy. This is the main thing to fix.

**Locked voice description** (paste into any voice or video model):
> Young Black American man, about 19, from the Seattle area. Low-to-mid warm voice with a little rasp, relaxed and confident, smiling while he talks. Casual Pacific Northwest delivery with light AAVE ("y'all", "don't get"), never a cartoon accent. Talks to the phone like it's his friend.

- Pitch: low-mid (around 110 to 130 Hz at rest), lifts a little on the hype line, never jumps to a bright, high read.
- Pace: about 2.3 to 2.7 words a second. Short hook lines with a beat of silence after each.
- Energy: 6/10 cool on the hook, 8/10 on the shout-out. Never yelling, never "announcer".
- Clone source: `voice-clone-source.mp3` (take 1 only, 7.3 s, single voice). `voice-sample-full.mp3` has both takes for listening.

## 6. Delivery notes (how to make take two better than take one)

1. **One voice the whole ad.** Same low warm timbre in the shout-out as in the hook; only the energy rises.
2. **Start mid-thought**, eyes on the lens, like he just hit record. No "hey guys".
3. **Land each short line, then stop.** "Embroidered." beat. "Not printed." beat.
4. **Smile on the payoff** ("One run only.") and finish with mouth closed, still looking at the lens, for half a second. No lip flap after the last word.
5. **Point, don't grab.** Taps or points at the chest badge; does not pull the hoodie toward the camera (that framing made the badge warp).
6. **Fewer words.** 10 s clip = 22 to 26 words max.

## 7. Pronunciation

| Word | Say it | Write it in spoken lines as |
|---|---|---|
| Postatees | **POH-stuh-teez** (stress on POH, "stuh" short, "teez" like tees) | `Poh-stuh-teez` |
| Everett | EV-rit (two syllables) | `Everett` |
| Marauders | muh-RAW-derz | `Marauders` |
| Mariner | MAIR-ih-ner | `Mariner` |

Video and speech models read the spoken text literally, so put the phonetic spelling in the dialogue and keep the real spelling for on-screen captions.

## 8. Prompt block (copy into any render)

> Jalen: a young Black man around 19 with warm medium-brown skin, short dark curly hair with a tight taper, thin mustache and light chin-strap beard, easy wide smile. He wears a deep navy pullover hoodie with a gold oval orca POSTATEES badge on the left chest, black drawstrings. Chest-up phone selfie from the driver's seat of a parked car. Keep the sleeves out of frame.
> Voice: low-to-mid warm young man's voice with slight rasp, relaxed and confident, casual Pacific Northwest delivery, smiling. Postatees is said POH-stuh-teez. Same voice for every line. Ends with mouth closed, looking at the lens.

## 9. Lock status

| Piece | Status |
|---|---|
| Look, wardrobe, setting, prompt block | Locked in this bible and in both apps |
| Reference images | Locked (720p from the ad) |
| Voice description and delivery | Locked as text |
| Exact voice (clone) | **Not locked yet.** Needs one paid call, see below |

## 10. Upgrades that cost money (not done, need Bambu's OK)

- **Fal Kling voice clone** (`fal-ai/kling-video/create-voice`): **$0.007 once**, returns a `voice_id`. Buffer Blaster then binds it to Jalen in every Kling v3 render. Voice-controlled clips cost $0.196/s instead of $0.168/s, so a 10 s clip goes from about **$1.68 to $1.96**.
- **1080p hero still** (Nano Banana edit on Fal from the three refs): about **$0.04** per image.
- **ElevenLabs Instant Voice Clone**: needs the Starter plan, **$1 for the first month, then $6 a month**. Not needed if the Kling voice is used.
