# Buffer Blaster
**Autonomous social media content production for Shopify brands.**

Hermes orchestrates. Seedance 2.0 generates. Buffer publishes. You approve.

---

## What it does

1. **Interviews** your client using the grill-me protocol (one question at a time)
2. **Researches** competitors, extracts viral outliers, analyzes Shopify LTV data
3. **Generates** UGC video prompts (Seedance 2.0 × Higgsfield), captions, and hooks
4. **Scores** every piece of content for viral potential (0–100, transparent breakdown)
5. **Queues** the top-scored posts for human approval via email + dashboard
6. **Publishes** approved content to Buffer on optimized platform-native schedules
7. **Improves** via flywheel — real engagement data updates future scoring weights

Human in the loop: **start** (interview + brief confirmation) and **end** (approve/reject).
Everything in the middle: autonomous.

---

## Niche support

| Niche | Video skill | Platform priority |
|-------|------------|-------------------|
| Food & Beverage | Seedance 2.0 food-bev cinematics | TikTok → Reels → Pinterest |
| Beauty & Skincare | UGC creator-style | Reels → TikTok → YouTube Shorts |
| Apparel & Accessories | UGC lifestyle/try-on | Reels → Pinterest → TikTok |
| Home & Lifestyle | Transformation/cozy | Pinterest → Reels → TikTok |

---

## Architecture

```
Master Hermes Orchestrator (VPS)
  └─ Per-client orchestrator (up to 50 parallel, Sandcastle)
       ├─ interviewer-leaf    → grill-me interview → brief.yaml
       ├─ researcher-leaf     → Apify scraping + outlier detection
       ├─ content-writer-leaf → captions + hooks (stop-slop filtered)
       ├─ video-prompter-leaf → Seedance 2.0 prompts → Higgsfield
       ├─ scorer-leaf         → viral scoring 0–100
       └─ publisher-leaf      → Buffer API → scheduled posts

Frontend: Next.js → Vercel (approval dashboard)
Database: Supabase (state, scores, posts, beads)
Tasks:    absurd (retry + resilience)
CLI:      mcp2cli (Hermes → Higgsfield programmatic)
Changes:  .beads/ (Steve Yegge format, reversible)
Flywheel: Dicklesworthstone ACFS (self-improving)
```

---

## Quick start

### Prerequisites
- Node.js ≥ 20
- Python ≥ 3.11
- VPS with ≥ 8GB RAM
- Accounts: Higgsfield, Buffer, Supabase, Apify, Airtable

### Setup

See [`docs/CLAUDE_CODE_WIRING.md`](docs/CLAUDE_CODE_WIRING.md) for the full Claude Code prompt
to wire everything to your VPS automatically.

```bash
git clone https://github.com/executiveusa/buffer-blaster-.git
cd buffer-blaster-
cp .env.example .env   # fill in your values
npm install
python scripts/sync_airtable.py  # download Airtable image gallery
npm run db:push                   # apply Supabase schema
npm run agent:start               # start Hermes orchestrator
```

### Run a client pipeline

```bash
# Start with interview
npm run interview -- --client-slug=brand-a

# After interview completes, run the full pipeline
npm run pipeline -- --client-slug=brand-a
```

---

## Key files

| File | Purpose |
|------|---------|
| `SYSTEM_PROMPT.md` | Master system prompt for Hermes |
| `SELF_DIGESTING_PROMPT.md` | Shareable self-contained workflow prompt |
| `agents/orchestrator/SOUL.md` | Hermes agent identity |
| `agents/orchestrator/hermes_config.yaml` | Hermes configuration |
| `scripts/client_pipeline.ts` | Sandcastle per-client workflow |
| `scripts/sync_airtable.py` | Airtable → GitHub image sync |
| `skills/grill-me/SKILL.md` | Client interview protocol |
| `skills/stop-slop/SKILL.md` | Anti-slop content guardrails |
| `skills/food-beverage/SKILL.md` | Seedance 2.0 food/bev video skill |
| `skills/ugc-video/SKILL.md` | UGC creator video skill |
| `skills/scoring/SKILL.md` | Viral scoring rubric |
| `supabase/migrations/001_initial_schema.sql` | Full database schema |
| `frontend/src/pages/review/...` | Human approval dashboard |
| `frontend/src/lib/buffer.ts` | Buffer API integration |
| `.beads/README.md` | Change tracking system |
| `docs/CLAUDE_CODE_WIRING.md` | VPS setup instructions |

---

## Reference repos

This system synthesizes and extends:

- [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) — Orchestrator
- [`mattpocock/sandcastle`](https://github.com/mattpocock/sandcastle) — Parallel workflows
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — Grill-me interview
- [`hardikpandya/stop-slop`](https://github.com/hardikpandya/stop-slop) — Anti-slop guardrails
- [`beshuaxian/higgsfield-seedance2-jineng`](https://github.com/beshuaxian/higgsfield-seedance2-jineng) — Food/bev video
- [`sirioberati/Seedance-2.0-AI-UGC`](https://github.com/sirioberati/Seedance-2.0-AI-UGC) — UGC video
- [`bradautomates/content-ideas`](https://github.com/bradautomates/content-ideas) — Research
- [`executiveusa/pauli-taste-skill`](https://github.com/executiveusa/pauli-taste-skill) — Taste standards
- [`executiveusa/pauli-Uncodixfy`](https://github.com/executiveusa/pauli-Uncodixfy) — Tone/voice
- [`earendil-works/absurd`](https://github.com/earendil-works/absurd) — Task resilience
- [`knowsuchagency/mcp2cli`](https://github.com/knowsuchagency/mcp2cli) — CLI bridge
- [`Dicklesworthstone/agentic_coding_flywheel_setup`](https://github.com/Dicklesworthstone/agentic_coding_flywheel_setup) — Self-improvement flywheel

---

## Gaps and known limitations

See `SELF_DIGESTING_PROMPT.md` → "Gaps this system knows about" for the full list.

Top 3:
1. **Video generation queue**: Higgsfield/Seedance has queues. Budget 2–10 hours.
2. **Scoring model cold start**: First run uses competitor proxy scores. Gets accurate after 2–3 cycles.
3. **Vercel project ID**: Not yet provided. Frontend deploy is pending.

---

## Contributing

This system is designed to be forked per agency or per client portfolio.
All skills are in `skills/` — modify them without touching the agent core.
All changes write beads to `.beads/` — everything is reversible.

---

## License

Free to use. Free to fork. Please attribute the source repos listed above.
