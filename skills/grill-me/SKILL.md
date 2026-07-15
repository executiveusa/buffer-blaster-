---
name: grill-me
description: >
  One-question-at-a-time client interview skill. Run before any content generation.
  Drills down on brand, customer, product, taste, and goals. Produces brief.yaml.
  Based on mattpocock/skills grill-me pattern. Never batch questions.
source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
---

# GRILL-ME — Client Interview Skill

## The Rule

One question. Wait for the answer. Then the next question.
Never ask two questions in one message.
Never summarize what they said before asking the next question.
Never explain why you're asking.
Just ask.

## When to use this skill

- Every new client, no exceptions
- Before any content generation
- When a client's brief feels incomplete mid-pipeline
- When a scoring model returns too many sub-60 scores (re-interview signal)

## The Interview Sequence

The questions below are the minimum. Based on answers, add follow-ups.
Trust your judgment on follow-ups — the goal is a brief.yaml good enough to
generate content that gets approved on the first pass.

---

### Q1 — The real description

> "What's the product? Describe it like you'd describe it to a stranger at a party —
> not the pitch version, the real version."

**What you're listening for:**
- Do they lead with features or with feeling?
- What language do they naturally use? (That's the brand voice)
- Do they sound proud, uncertain, excited, protective?
- What do they leave out that a customer would care about?

**Follow up if:** The answer sounds like a press release. Ask again.
"Try it without any adjectives. What does it actually do?"

---

### Q2 — The real customer

> "Who's your best customer? Not demographics — who is this *person*?
> What do they talk about? What do they worry about? What do they brag about?"

**What you're listening for:**
- Specificity (a real person) vs. generality (a demographic segment)
- What drives the purchase — aspiration, problem-solving, identity, gift?
- How they talk about the product to others (that's the hook)

**Follow up if:** They give you demographics. Ask: "Give me one specific person.
Not a persona. A person you've actually talked to."

---

### Q3 — Content that worked on them

> "Show me 3 posts or videos from any brand — yours or a competitor —
> that made you think 'I wish we made that.' What made them work?"

**What you're listening for:**
- Their visual aesthetic instincts
- The energy they want to project
- Platform preferences (even if unstated)
- What "good" looks like in their mind

**Follow up if:** They can't name 3. Ask them to name 1 and describe what made
it stop their scroll. That's the brief.

---

### Q4 — Content that flopped

> "What has flopped for you recently? What did you think would work that didn't?"

**What you're listening for:**
- Patterns in the failures (format? hook? timing? platform?)
- Self-awareness about what they don't know
- Direction: "avoid this entire category of content"

**Follow up if:** They say "nothing has flopped." Either they're not posting much
or they're not tracking. Ask: "What's the post you're most embarrassed by?"

---

### Q5 — Shopify data

> "What does your Shopify data tell you about your best customers?
> Upload your CSV or share: average order value, top 3 products, repeat purchase rate, top locations."

**What you're listening for:**
- LTV signals (repeat buyers = loyalists, high AOV = aspirational customers)
- Top products = what actually converts (may not be what they think)
- Location = regional cultural context for content tone
- Repeat rate = whether retention or acquisition content matters more

**If no CSV yet:** Proceed with what they share verbally.
Flag in brief.yaml: `ltv_data: verbal_only — CSV needed for scoring optimization`

---

### Q6 — Brand voice

> "What's your brand voice? Give me 3 adjectives that describe it AND
> 3 words that would never appear in your copy."

**What you're listening for:**
- Adjectives reveal the aspiration
- "Never" words reveal where past content went wrong or what feels off-brand

**Follow up if:** Their 3 adjectives contradict each other (e.g., "luxury" and "approachable").
Ask: "If you had to pick one, which matters more?" That's the brand.

---

### Q7 — Platform priority

> "What platforms are most important to you? Rank them."

**What you're listening for:**
- Where their audience already is
- Where they want to grow (may differ)
- Budget signal: TikTok = volume, Pinterest = long-tail, YouTube Shorts = discovery

**Follow up if:** They say "all of them." Ask: "If you could only post on one
for the next 30 days, which would it be?" That's the primary platform.

---

### Q8 — Category truth

> "What's the one thing most people get wrong about your category?"

**What you're listening for:**
- Their category expertise (this becomes a hook)
- The differentiated angle that no competitor content addresses
- The thing customers discover post-purchase that they didn't expect

This answer often produces the best hooks. Use it directly.

---

### Q9 — Visual references

> "Any visual references? Share your Airtable gallery link or upload images
> that show the aesthetic you're going for."

**What you're listening for:**
- Their definition of "quality" visually
- Color palette instincts
- UGC vs. produced preference
- Whether they have enough assets or need Seedance to generate

**If no Airtable link:** Note in brief.yaml. Sync when they provide it.

---

### Q10 — Primary goal

> "What's your content goal right now — awareness, conversions, or retention?"

**What you're listening for:**
- This sets the entire content strategy
- Awareness: top-of-funnel, entertainment hooks, broad appeal
- Conversions: problem/solution, social proof, product demos
- Retention: loyalty content, behind-the-scenes, community

---

## After Q10 — Build the Brief

Synthesize everything into a `brief.yaml` and read it back:

```yaml
client:
  name: [name]
  slug: [kebab-case-slug]
  niche: [food-beverage|beauty-skincare|apparel|home-lifestyle]
  shopify_url: [url if given]

product:
  name: [product name]
  real_description: [their own words from Q1, not cleaned up]
  price_point: [budget|mid|premium|luxury — inferred]

customer:
  persona: [1 paragraph — the specific person from Q2]
  ltv_data_source: [csv|verbal|none]
  ltv_summary: [key figures if available]
  top_products: [list from Shopify or verbal]

brand_voice:
  adjectives: [3 words from Q6]
  never_say: [3 words from Q6]
  reference_content:
    - [url or description from Q3 — what they wish they'd made]

content_strategy:
  goal: [awareness|conversions|retention from Q10]
  platforms: [ranked list from Q7]
  primary_platform: [first in ranked list]
  posting_frequency: [per week — ask if not stated]

taste:
  airtable_gallery: [url if provided]
  visual_style: [inferred from Q3 + Q9]
  energy: [inferred from their language throughout]

research_flags:
  flopped_content: [summary from Q4]
  category_truth: [their exact words from Q8]
  avoid_patterns: [inferred from Q4]
```

**Read it back:** "Here's what I heard. Anything off?"
Wait for confirmation before starting the pipeline.

---

## Red Flags (re-ask or flag)

🚩 They describe the customer as "everyone" → Re-ask Q2
🚩 Their adjectives are contradictory → Re-ask Q6
🚩 They don't know their top Shopify product → Flag: scoring will be limited
🚩 They've never looked at competitor content → Flag: research phase will carry more weight
🚩 Their goal is all three (awareness + conversions + retention) → Ask Q10 again with a forced choice

---

## The Brief is a Contract

Once confirmed, the brief.yaml is the source of truth for:
- Research phase (who to scrape, what to look for)
- Content ideation (hooks, formats, captions)
- Scoring (audience match dimension)
- Approval (what the human expects to see)

Do not deviate from the brief without re-interviewing.
Do not "improve" the brief by second-guessing the client's answers.
Their exact words from Q1 and Q8 are often the best hooks. Use them.
