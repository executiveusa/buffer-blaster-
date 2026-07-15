---
name: stop-slop
description: >
  Anti-AI writing guardrails for all verbal content. Use on every caption, hook,
  script, email subject, button label, and UI copy before it leaves the pipeline.
  Triggers automatically on all text output. Source: hardikpandya/stop-slop
source: https://github.com/hardikpandya/stop-slop
---

# STOP SLOP — Anti-AI Writing Guardrails

If it sounds like a pull-quote, rewrite it.

## BANNED PHRASES (auto-reject, rewrite required)

### Throat-clearing openers
- "In today's [adjective] world..."
- "Now more than ever..."
- "It's worth noting that..."
- "Before we dive in..."
- "Let's take a look at..."
- "As we explore..."

### Emphasis crutches
- Certainly / Indeed / Obviously / Clearly / Absolutely
- Very / Extremely / Incredibly / Truly / Deeply / Highly

### Business jargon
- Leverage / Synergy / Ecosystem / Journey / Space / Landscape
- Game-changing / Revolutionary / Transformative / Groundbreaking
- Unlock / Empower / Seamless / Robust / Scalable (when used as filler)

### Vague declaratives
- "Here's what you need to know..."
- "The results speak for themselves."
- "The bottom line is..."
- "At the end of the day..."
- "Make no mistake..."

### Meta-commentary
- "As an AI language model..."
- "I should note that..."
- "It's important to understand that..."
- "This is a complex topic..."

## STRUCTURAL PATTERNS BANNED

### Binary contrasts
❌ "Not just X, but Y"
❌ "This isn't about X. It's about Y."
✓ Just say Y.

### Negative listing
❌ Start by saying what it isn't before what it is.
✓ Say what it is.

### Dramatic fragmentation
❌ Short.
❌ Punchy.
❌ Fragments for effect.
✓ Write complete sentences that carry the idea.

### Rhetorical setup
❌ "But what does that mean for you?"
❌ "So what's the takeaway?"
✓ Give the meaning directly.

### False agency
❌ "Our brand believes in..."
❌ "We're committed to..."
✓ Show it through the product or the customer.

### Passive voice as default
❌ "The product was designed to..."
✓ "We designed the product to..."

## WHAT GOOD LOOKS LIKE

Write like the brand's best customer talks about the product to a friend.

- Specific ("lasts 3 weeks" not "long-lasting")
- Sensory for food/beauty ("you can smell it before you open it")
- Present tense for energy
- Active voice
- One idea per sentence
- No setup — start with the point

## SCORING RUBRIC (5 dimensions, before/after test)

Run this check on every text output before it leaves the pipeline:

1. **Opener** — Does it start with the actual point? (Not a setup, not throat-clearing)
2. **Adverb count** — Are there any adverbs? (Target: zero)
3. **Pull-quote test** — Could this sentence appear on a motivational poster? (Bad sign)
4. **Person test** — Could a real person say this to another person without sounding weird?
5. **Jargon count** — Any banned words from the list above? (Target: zero)

If any of these fail: rewrite. Don't negotiate. Rewrite from scratch.

## FOOD & BEVERAGE SPECIFIC

Don't describe what a product does. Describe what it feels like to use it.
Don't say "delicious." Describe the sensation that makes it delicious.

❌ "Our sauce is incredibly delicious and pairs perfectly with any dish."
✓ "Three weeks in the fridge and it still smells like the morning you made it."

## BEAUTY SPECIFIC

Don't promise transformation. Describe the specific experience.

❌ "Our moisturizer will transform your skin and give you the confidence you deserve."
✓ "Six hours later, your face still feels like you just washed it."

## APPAREL SPECIFIC

Don't describe the fabric. Describe the feeling of wearing it.

❌ "Made with premium sustainable materials for maximum comfort and style."
✓ "You forget you're wearing it. That's the point."
