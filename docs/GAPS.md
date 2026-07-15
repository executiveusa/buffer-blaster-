# GAPS & HOLES — Buffer Blaster
# Identified after initial plan. Fill these before going to production.

---

## CRITICAL GAPS (must resolve before first client)

### GAP 1: Vercel Project ID
**Status:** Pending user input
**Impact:** Frontend approval dashboard cannot deploy
**Resolution:** User provides project ID → add to VERCEL_PROJECT_ID env var → re-run `npm run deploy:frontend`

### GAP 2: Higgsfield Video Queue Handling
**Status:** Partially handled (absurd retry), but async job polling not fully built
**Impact:** Pipeline may appear to hang waiting for video generation (can take 2–10 hours)
**Resolution needed:**
- Add webhook or polling loop in `video-prompter-leaf`
- Decouple video generation from scoring (score text content now, add video URL when ready)
- Notify human that videos are still processing in approval email
**File to update:** `scripts/client_pipeline.ts` → Step 4

### GAP 3: Shopify CSV Parser
**Status:** Schema mentions it, no parser implemented
**Impact:** LTV data analysis (audience_match scoring dimension) will be limited to verbal input
**Resolution needed:** Build `scripts/parse_shopify_csv.py`
  - Parse customer export format (first_name, last_name, email, total_spent, orders_count)
  - Identify top 20% by total_spent
  - Extract: AOV, repeat rate, top products, location distribution
  - Write to Supabase `interviews.answers_json` as `ltv_analysis` key

### GAP 4: Competitor Scraping — Apify Config
**Status:** Referenced (bradautomates/content-ideas pattern) but Apify actor IDs not specified
**Impact:** Research phase will fail if Apify actors aren't configured
**Resolution needed:**
- Confirm Apify actor IDs for: Instagram scraper, TikTok scraper, YouTube Shorts scraper
- Add actor IDs to `config/apify_actors.json`
- Build `scripts/research.ts` that calls these actors with niche-specific keywords

### GAP 5: Email Delivery for Approval
**Status:** Approval email described but no email provider configured
**Impact:** Human never receives approval notification
**Resolution needed:** Choose one:
  - Resend (recommended — simple API, free tier)
  - SendGrid
  - Postmark
  Add `EMAIL_API_KEY` + `EMAIL_FROM` to env vars. Build `lib/email.ts`.

### GAP 6: Scoring Cold Start — No Engagement Data
**Status:** Acknowledged in SELF_DIGESTING_PROMPT.md but not solved
**Impact:** First 2–3 cycles, scoring is based on heuristics, not real engagement
**Resolution needed:**
- Build fallback scoring for cold start: use competitor outlier engagement rates as proxy
- Track: when a post was approved by human (that's the primary training signal)
- After 10+ posts approved, weight flywheel scores more heavily

---

## MEDIUM GAPS (should resolve in first sprint)

### GAP 7: Taste Skill — Content Missing
**Status:** Referenced from executiveusa/pauli-taste-skill but not included in repo
**Impact:** "Taste standards" dimension in scoring has no concrete spec
**Resolution needed:** User to provide taste skill content → add to `skills/taste/SKILL.md`

### GAP 8: mcp2cli — Hermes Integration Not Tested
**Status:** Install steps documented, actual Hermes → mcp2cli call not written
**Impact:** Programmatic video generation from Hermes leaf agents unverified
**Resolution needed:**
- Test `mcp2cli call higgsfield generate_video --input='...'`
- Wrap in absurd retry in `video-prompter-leaf`
- Document exact CLI syntax in `skills/ugc-video/SKILL.md`

### GAP 9: Buffer API — Platform Profile Mapping
**Status:** Profile fetching written, but matching by platform is approximate
**Impact:** Posts may go to wrong profile if client has multiple accounts per platform
**Resolution needed:**
- During client onboarding, store explicit Buffer profile IDs per platform in Supabase
- Add to grill-me: "What are your Buffer profile IDs? (or we can fetch them)"
- Store in `clients.buffer_profile_ids` as `{"tiktok": "id", "instagram": "id"}`

### GAP 10: Sandcastle Version Compatibility
**Status:** Sandcastle is early-stage (mattpocock). API may change.
**Impact:** `client_pipeline.ts` may need syntax updates after Sandcastle updates
**Resolution needed:**
- Pin Sandcastle to a specific commit in package.json
- Monitor `mattpocock/sandcastle` upstream via CI workflow (already set up)
- Add integration test for pipeline script in CI

### GAP 11: Flywheel → Skills Loop Not Automated
**Status:** Described conceptually, not implemented
**Impact:** Skills won't actually self-improve — it will stay at v1.0.0 forever
**Resolution needed:**
- Build `scripts/flywheel.ts`:
  - After N posts published, query engagement data from Buffer
  - Compare top-performing vs. bottom-performing by niche
  - Extract pattern differences
  - Write to `context/winning_patterns.md` per client
  - Update `config/scoring_weights.json`
  - Open GitHub PR with skill improvement suggestions

---

## LOW PRIORITY GAPS (future sprints)

### GAP 12: Pinterest Video Format
- Pinterest has its own video spec (2:3 ratio, 4s–15min)
- Current video prompts default to 9:16 or 16:9
- Need Pinterest-specific prompt variant in food-beverage and ugc-video skills

### GAP 13: YouTube Shorts Metadata
- YouTube requires title + description (not just caption)
- Buffer may not support all YouTube metadata fields
- Need to check Buffer YouTube API support and generate title separately

### GAP 14: Multi-language Support
- Shopify brands often serve Spanish-speaking customers (especially given Mexico City context)
- Stop-slop guardrails are English-only
- Long-term: build Spanish variant of stop-slop + caption generation

### GAP 15: Hermes Agent Memory Between Sessions
- If VPS restarts, Hermes loses in-memory context of running pipelines
- Need: Supabase-backed session state so pipelines can resume after interruption
- Partially handled by beads, but not full pipeline resume

### GAP 16: Approval Dashboard — Mobile
- Current frontend is desktop-first (max-w-3xl centered layout)
- Many approvals will happen on mobile
- Need: ensure card layout, video player, buttons work on 375px viewport
- Steve Krug: "Don't Make Me Think" applies doubly on mobile

---

## QUESTIONS TO FILL REMAINING GAPS

1. **Vercel project ID?** → Unblocks frontend deploy
2. **Email provider preference?** → Resend / SendGrid / Postmark → Unblocks approval notifications
3. **Apify actor IDs for your scrapers?** → Unblocks research phase
4. **Taste skill content?** → From executiveusa/pauli-taste-skill → Unblocks scoring dimension
5. **Buffer profile IDs per client?** → Improves publishing accuracy
6. **Engagement data access?** → Buffer Analytics, or platform-native APIs? → Unblocks flywheel

---

*Last updated: 2026-07-14*
*Next review: after first client pipeline run*
