---
name: ugc-video
description: >
  Generate UGC-style video prompts for Seedance 2.0 on Higgsfield for Beauty, 
  Apparel, and Home & Lifestyle brands. Use when creating influencer-style product
  reviews, demos, unboxings, lipsync, or lifestyle ads. Based on Sirio Berati's
  AI UGC workflow. Source: sirioberati/Seedance-2.0-AI-UGC
source: https://github.com/sirioberati/Seedance-2.0-AI-UGC
---

# UGC VIDEO SKILL — Seedance 2.0 × Higgsfield

## The Two Prompt Styles

Seedance 2.0 UGC uses two fundamentally different prompt formats:

### Style A: Descriptive (You control everything)
Write exactly what happens, frame by frame. Who, what, how, where, energy.
Use when: you have a specific vision. Max control.

### Style B: Outcome-Driven (Model interprets)
Describe the result you want, not the steps to get there.
Use when: you want creative variation. Less control, more surprise.

**Default to Style A for production ads.** Use Style B for creative exploration.

---

## STYLE A: MASTER TEMPLATE

```
Using @image1 as the product reference, create a [UGC style descriptor] video
featuring a [specific person description — age, energy, style, NOT ethnicity].

They are [specific action with product — what exactly are they doing?] while
[environment description — where, lighting, what's around them].

They [specific gesture or movement] as they [speak to camera / hold product /
demonstrate use]. The composition is [vertical 9:16 / horizontal 16:9].

Lighting is [soft natural / warm studio / golden hour / ring-lit].
Energy is [casual recommendation / excited discovery / expert review /
aspirational lifestyle / ASMR calm / before-after reveal].
The tone feels like [specific comparison — a friend's story, a Reddit comment,
a skincare subreddit post, a fashion haul TikTok].

[Optional: add specific dialogue direction if lipsync]
```

---

## NICHE PLAYBOOKS

### Beauty & Skincare

**Mindset**: Trust, transformation, specificity, skin close-ups.

**Proven formats:**
1. **Application demo** — Creator applies product in real time. Camera tight on skin.
2. **Before/after reveal** — Split screen or time-cut showing change.
3. **Ingredient spotlight** — Creator holds up bottle, zooms to label, explains one ingredient.
4. **Morning routine cameo** — Product appears naturally in a wider routine.
5. **Podcast-style review** — Creator speaks candidly, product on desk, not in hand.

**Example prompt (Style A, skincare):**
```
Using @image1 as the product reference, create a natural UGC skincare review video
featuring a woman in her early 30s with a fresh, no-makeup look and warm energy.

She is applying the serum to her face in front of a bathroom mirror, using her
fingertips to press it into her cheekbones and under-eye area. The bathroom is
softly lit with natural daylight from a window off-frame left.

She glances at camera mid-application with a slight smile — not performed, just
caught in a real moment. Composition is vertical 9:16.

Lighting is soft diffused natural. Energy is honest recommendation — like a friend
who genuinely uses this and wants you to know about it. No ring light glow.
No branded backdrop. This looks like someone's real bathroom on a Tuesday morning.
```

**Things that kill beauty UGC:**
- Overly performed reactions
- Unnaturally perfect skin in the "before"
- Generic "glowing skin" language
- Harsh artificial lighting
- Looking directly at camera the whole time (breaks naturalism)

---

### Apparel & Accessories

**Mindset**: Aspiration, lifestyle, how it moves, how it makes you feel.

**Proven formats:**
1. **Try-on haul** — Multiple outfits, quick cuts, genuine reactions.
2. **Day-in-the-life** — Product worn naturally across different settings.
3. **Styling multiple ways** — One piece shown 3 ways.
4. **Compliment-fishing setup** — Creator mentions getting asked about what they're wearing.
5. **Closet pull** — Creator recommending from their own wardrobe.

**Example prompt (Style A, apparel):**
```
Using @image1 as the product reference, create a natural try-on style TikTok
featuring a woman in her mid-20s with a casual, confident style — jeans and
white tee as baseline, switching into the featured piece.

She's in a bright bedroom with good natural light, a full-length mirror visible
at frame edge. She pulls the item from a hanger, holds it up to herself,
then cuts to wearing it, doing a natural slow 360 turn.

Her hands adjust the fit at the waist — a real gesture, not staged.
She looks at herself in the mirror with a "yeah, that works" expression,
not the camera. Vertical 9:16.

Energy: the way someone actually acts when they find something that fits
perfectly. Understated satisfaction. Not a sales pitch.
```

---

### Home & Lifestyle

**Mindset**: Transformation, cozy, "I made this space better", process reveal.

**Proven formats:**
1. **Before/after transformation** — Space before → product → space after.
2. **Unboxing to placement** — Product unboxed and immediately styled.
3. **Cozy setup reveal** — Slow reveal of a styled corner or room.
4. **Sustainability/quality callout** — Durability, materials, how it ages.
5. **Morning/evening ritual** — Product as part of a home routine.

**Example prompt (Style A, home):**
```
Using @image1 as the product reference, create a slow-reveal home styling video
showing a living room corner being transformed.

Start wide: the corner is bare except for a floor lamp. A pair of hands enters
frame and sets the featured product (a ceramic vase) on a small side table.
Then a single stem of dried flowers. Then a small stack of two books.
Each placement is deliberate — a 2-second pause between each.

Final shot: slow zoom out from the vase, revealing the full styled corner.
Warm afternoon light from window right. No voiceover. No text overlay needed —
the styling tells the story.

Composition shifts from 16:9 wide to a final vertical 9:16 close-up of the vase.
Energy: the satisfaction of getting a space exactly right. Quiet. Intentional.
```

---

## LIPSYNC WORKFLOW

For lipsync ads where you supply the voiceover:

1. Record your own voice saying the script
2. Upload audio as @audio1
3. Select a creator face (Higgsfield face library or your upload)
4. Prompt format:

```
Using @audio1 as the voiceover, create a lipsync video with a [creator description].
They are speaking directly to camera in a [setting]. Their expression matches
the energy of the audio — [calm and conversational / excited discovery / honest review].
Vertical 9:16. [Lighting description].
```

---

## APP/SOFTWARE REVIEW FORMAT

For Shopify apps, digital products, or software UI:

```
Using @image1 as the UI screenshot reference, create an iPhone-style vertical
UGC app review featuring a [creator description] in the foreground holding a
smartphone upright in one hand, clearly showing the screen to the viewer.

The phone is angled slightly toward camera so the interface is readable.
Creator is speaking directly to camera with [energy descriptor — excited /
practical / "I just found this" energy], slightly leaning forward and presenting
the phone like evidence — like they're sharing something they actually use.

The screen displays [brief description of what should appear on screen].
Composition: vertical 9:16. Creator takes up left 2/3 of frame,
phone in right hand visible at frame right.
```

---

## A/B TESTING PROTOCOL

Run 2 variants per content idea before committing to full production:

**Variant A**: Style A prompt (fully descriptive)
**Variant B**: Style B prompt (outcome-driven)

Score both on:
- Hook strength (first 2 seconds)
- Naturalness of creator behavior
- Product visibility
- Platform fit

Pick the higher scorer. Kill the other. No sentiment.

---

## COMMON MISTAKES

1. **Over-directing performance** — "She smiles with genuine excitement" is direction.
   Seedance reads it literally and produces a smile that looks forced.
   Better: describe the situation that would naturally produce that expression.

2. **Forgetting the product** — UGC is about the product. Every 3–5 seconds,
   the product should be visible or referenced.

3. **Too much text direction** — If you need 5 lines to describe what someone says,
   use lipsync with your own audio instead.

4. **Generic "influencer" description** — Avoid "a beautiful young influencer."
   Be specific: "a woman in her late 20s, undercut hair, wearing a linen shirt,
   the kind of person who has opinions about coffee grinders."

5. **Ignoring platform** — TikTok UGC = fast cuts, captions baked in, trending audio.
   Instagram Reels = slightly more polished, slower reveal. Pinterest = aspirational
   lifestyle, less talking-head. Prompt differently per platform.
