# CLAUDE CODE HANDOFF — STAVARAI PLATFORM
# Paste this entire file into Claude Code to execute the build.
# This is the complete instructions. Do not supplement with your own assumptions.

---

## IDENTITY

You are Claude Code, executing a private enterprise AI platform build.
The client is Stavarai. This is his platform. He is the only admin.
You are building for deployment to Vercel (frontend) and his VPS (agents + backend).

Before you write any code:
1. Read `CLAUDE.md` (root ICM router)
2. Read `00_context/PROJECT.md` (identity + positioning)
3. Read `02_specs/TDD_SPEC.md` (all features as tests)
4. Then and only then: begin Phase 1

---

## MISSION

Build a private, enterprise-grade AI content operations platform.
It is accessed by one person: Stavarai.
Demo mode uses password: `BLASTER2026` — no OAuth required.
Everything behind that password is personal, high-security, and enterprise-quality.

This is NOT a demo. This is NOT a prototype.
Build it as if a Fortune 500 company will audit the code.

---

## STEP 0: ENVIRONMENT SETUP

```bash
# Verify environment
node --version    # must be >= 20
python3 --version # must be >= 3.11
cargo --version   # must be installed (rustup)
supabase --version

# Clone and set up
git clone https://github.com/executiveusa/buffer-blaster-.git /opt/buffer-blaster
cd /opt/stavarai-platform
npm install
pip install -r requirements.txt --break-system-packages

# Copy env template
cp .env.example .env
# --- STOP HERE ---
# Prompt Stavarai for each env var. Do not proceed without them.
# Required minimum: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
```

---

## STEP 1: INSTALL HERMES + SKILLS

```bash
# Install Hermes Agent
git clone https://github.com/NousResearch/hermes-agent.git /opt/hermes
cd /opt/hermes && npm install

# Copy Buffer Blaster skills into Hermes
cp -r /opt/buffer-blaster/skills/* ~/.hermes/skills/
cp /opt/buffer-blaster/agents/orchestrator/SOUL.md ~/.hermes/SOUL.md

# Register Higgsfield skills globally
mkdir -p ~/.hermes/skills/higgsfield
cat > ~/.hermes/skills/higgsfield/CONTEXT.md << 'EOF'
# Higgsfield Skills — Global Registration
# Available to all Hermes agents in this installation

SKILLS:
  food-beverage: ~/.hermes/skills/food-beverage/SKILL.md
  ugc-video:     ~/.hermes/skills/ugc-video/SKILL.md
  scoring:       ~/.hermes/skills/scoring/SKILL.md
  stop-slop:     ~/.hermes/skills/stop-slop/SKILL.md
  grill-me:      ~/.hermes/skills/grill-me/SKILL.md
  taste:         ~/.hermes/skills/taste/SKILL.md

MCP SERVERS:
  higgsfield: https://mcp.higgsfield.ai/mcp

CLI BRIDGE:
  mcp2cli: /opt/mcp2cli/mcp2cli call higgsfield {tool} --input '{json}'
EOF

# Install mcp2cli for Higgsfield CLI bridge
git clone https://github.com/knowsuchagency/mcp2cli.git /opt/mcp2cli
cd /opt/mcp2cli && pip install -e . --break-system-packages
mcp2cli config add higgsfield --url https://mcp.higgsfield.ai/mcp

# Verify Hermes loads skills
hermes status
# Expected: "7 skills loaded | MCP: higgsfield ✓"

# Write install bead
echo '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","action":"hermes-installed","reversible":true}' \
  > .beads/$(date -u +%Y-%m-%d_%H-%M)_hermes-install.bead
```

---

## STEP 2: RUST CORE BUILD

```bash
cd rust_core

# Create Rust project structure
cargo new stavarai_core --lib
cd stavarai_core

# Cargo.toml
cat > Cargo.toml << 'EOF'
[package]
name = "stavarai_core"
version = "0.1.0"
edition = "2021"

[lib]
name = "stavarai_core"
crate-type = ["cdylib", "rlib"]

[dependencies]
aes-gcm = "0.10"
rand = "0.8"
sha2 = "0.10"
hmac = "0.12"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1", features = ["full"] }
axum = "0.7"
tower = "0.4"
chrono = { version = "0.4", features = ["serde"] }

[dev-dependencies]
tokio-test = "0.4"
EOF

# Write FAILING tests first (TDD)
# See: 03_tests/rust/test_encryption.rs
# See: 03_tests/rust/test_auth_middleware.rs
# See: 03_tests/rust/test_rate_limiter.rs
# See: 03_tests/rust/test_job_queue.rs

# Run tests — they must FAIL first
cargo test
# Expected: FAILED (tests exist, implementation doesn't)

# Now implement src/lib.rs with:
# - AES-256-GCM encryption/decryption
# - Session token generation + validation
# - Token bucket rate limiter (per-IP, per-route)
# - Async job queue with persistence

# Run tests again — they must PASS
cargo test
# Expected: test result: ok. X passed; 0 failed

# Build release
cargo build --release
cp target/release/libstavarai_core.so ../api/
```

**Implementation requirements for Rust core:**

```rust
// src/lib.rs structure
pub mod encryption {
    // AES-256-GCM
    // encrypt(plaintext: &str, master_key: &[u8; 32]) -> Result<String, Error>
    // decrypt(ciphertext: &str, master_key: &[u8; 32]) -> Result<String, Error>
    // mask_key(key: &str) -> String  // "sk-•••••••••[last4]"
}

pub mod auth {
    // generate_session_token() -> String  // 256-bit random, base64url
    // validate_token(token: &str, secret: &[u8]) -> Result<Claims, Error>
    // axum_middleware() -> impl Layer  // rejects invalid tokens in <1ms
}

pub mod rate_limiter {
    // TokenBucket: per key (IP or session), configurable rate
    // check(key: &str, route: &str) -> Result<(), RateLimitError>
    // RateLimitError includes retry_after: Duration
}

pub mod job_queue {
    // enqueue(job: Job) -> Result<JobId, Error>
    // dequeue() -> Option<Job>  // workers poll this
    // update_status(job_id: JobId, status: JobStatus)
    // persistent: SQLite or flat file (no Redis dependency)
}
```

---

## STEP 3: FASTAPI BACKEND

```bash
cd api/

# requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.8.0
sqlalchemy==2.0.36
supabase==2.7.0
pandas==2.2.0
httpx==0.27.0
python-multipart==0.0.9
python-telegram-bot==21.0
whisper-openai==20231117
absurd==0.1.0  # earendil-works/absurd
firecrawl-py==0.0.16
EOF

pip install -r requirements.txt --break-system-packages

# Project structure (ICM-compliant)
mkdir -p {routers,services,models,middleware,db}
```

**File: `api/main.py`**
```python
# FastAPI app entry point
# Imports Rust middleware via ctypes or PyO3
# All routes: /api/admin/* require Rust auth middleware
# Health: GET /api/health → { status: "ok", version: "1.0.0" }
```

**Required routes (implement after tests pass):**

```
Authentication:
  POST /api/auth/verify          → verify BLASTER2026 → session token
  POST /api/auth/logout          → invalidate token

Clients:
  GET  /api/admin/clients        → list all clients (master table)
  POST /api/admin/clients        → create client + Supabase schema
  GET  /api/admin/clients/{id}   → single client with stats
  POST /api/admin/clients/{id}/shopify-csv → upload + parse
  POST /api/admin/clients/{id}/sync-airtable → trigger async sync

Pipeline:
  POST /api/admin/pipeline/{client_id}/run → trigger Hermes pipeline
  GET  /api/admin/pipeline/{client_id}/status → real-time via SSE
  POST /api/admin/pipeline/{client_id}/cancel → abort + write bead

Content:
  GET  /api/admin/content/{client_id} → approval queue
  POST /api/admin/content/{unit_id}/approve → approve + queue Buffer
  POST /api/admin/content/{unit_id}/reject → reject + notify agent

Settings:
  GET  /api/admin/settings → all settings (keys masked)
  PUT  /api/admin/settings → update (Rust encrypts keys)
  POST /api/admin/settings/test/{service} → test API connection

Voice:
  POST /api/voice/command → VisionClaw webhook → Hermes command

Research:
  POST /api/admin/research/scan-url → Firecrawl → competitor analysis
  POST /api/admin/research/competitors/{client_id} → Apify scrape

Blog:
  GET  /api/blog/posts → all published posts
  POST /api/admin/blog/posts → create draft
  PUT  /api/admin/blog/posts/{id} → update
  POST /api/admin/blog/posts/{id}/publish → publish + SSG rebuild
```

---

## STEP 4: SUPABASE SETUP (Stavarai's Account)

```bash
# Connect to Stavarai's Supabase project
supabase link --project-ref [STAVARAI_PROJECT_REF]

# Apply migrations
supabase db push

# Migration: 001_master_schema.sql
# Creates public.clients, public.beads, public.settings (encrypted), public.blog_posts

# Migration: 002_client_isolation.sql
# Function: create_client_schema(slug TEXT)
# Creates schema_{slug} with all 8 buffer-blaster tables
# RLS: only service_role can access any schema_{slug}

# Seed demo data (for Vercel demo)
supabase db seed --file seeds/demo_data.sql
```

**Critical migration — client isolation:**

```sql
-- 002_client_isolation.sql
CREATE OR REPLACE FUNCTION create_client_schema(client_slug TEXT)
RETURNS void AS $$
BEGIN
  -- Create isolated schema
  EXECUTE format('CREATE SCHEMA IF NOT EXISTS schema_%I', client_slug);
  
  -- Create all tables in the new schema
  EXECUTE format($$
    CREATE TABLE IF NOT EXISTS schema_%I.content_units (
      id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
      -- ... full buffer-blaster schema
    )
  $$, client_slug);
  
  -- RLS: only service_role
  EXECUTE format('ALTER TABLE schema_%I.content_units ENABLE ROW LEVEL SECURITY', client_slug);
  
  -- Log bead
  INSERT INTO public.beads (action, notes, reversible)
  VALUES ('schema-created', format('Client schema created: schema_%s', client_slug), true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## STEP 5: NEXT.JS FRONTEND

```bash
cd frontend/

# Initialize with TailAdmin (best free, MIT, AI-ready)
npx create-next-app@latest . --typescript --tailwind --app
npm install @shadcn/ui tailwindcss-animate lucide-react

# Install TailAdmin free components
# Source: https://github.com/TailAdmin/free-react-tailwind-admin-dashboard
# Copy components to src/components/ui/tailadmin/

# Customize TailAdmin:
# 1. Remove all TailAdmin branding
# 2. Apply Stavarai color scheme:
#    --color-primary: #6366F1 (indigo)
#    --color-background: #0F1117 (near black)
#    --color-surface: #1A1D27 (dark surface)
#    --color-text: #F1F5F9 (light)
```

**Critical pages to build:**

### `/` — Landing Page

```tsx
// Full-viewport hero. Dark cinematic. No startup-gradient.
// Typography: Geist Display (editorial) + Geist Sans (body)
// Hero headline choices (pick the one that scores highest in A/B):
//   A: "Your team is working 60-hour weeks. AI doesn't sleep."
//   B: "Social media for 20 brands. One Tuesday afternoon."
//   C: "They post every day. You're still planning Monday's content."
// 
// Sections:
//   1. Hero (full-screen)
//   2. Pain points (4 cards — specific, not vague)
//   3. How it works (3 steps — no jargon)
//   4. Results (numbers, not percentages)
//   5. Blog preview (3 latest posts)
//   6. CTA (email capture or contact)
//   7. Footer (blog link + admin link — subtle)
//
// NO: tech buzzwords, generic "AI-powered" language, stock photos
// YES: editorial tone, specifics, the language of a tired agency owner
```

### `/admin` — Password Gate + Dashboard

```tsx
// BLASTER2026 password gate — simple, no branding of the platform name
// On success: localStorage.setItem('stavarai_auth', sessionToken)
// Dashboard:
//   - Greet: "Welcome back, Stavarai." (no exclamation point)
//   - First visit: OnboardingOverlay component (7-step walkthrough)
//   - Main: client cards with pipeline status, content waiting
//   - Sidebar: Clients | Pipelines | Content | Blog | Settings | Analytics
```

### `/admin/settings` — Settings Panel

```tsx
// Tabbed settings:
// Tab 1: AI Providers — dropdown + key + test button
// Tab 2: Integrations — Higgsfield, Buffer, Airtable, Apify, Firecrawl
// Tab 3: Agent Config — sliders for concurrency, timeout
// Tab 4: MCP Servers — list + add button
// Tab 5: Voice Control — Telegram config + VisionClaw URL
// Tab 6: API Guide — "What you need and where to get it"
//
// Each key field:
//   - Masked by default (show last 4 chars)
//   - "Edit" button to reveal + change
//   - "Test" button calls /api/admin/settings/test/{service}
//   - Green checkmark or red X based on test result
```

### `/blog` + `/blog/[slug]` — Public Blog

```tsx
// Static site generation (SSG) — fast, SEO-optimized
// No tracking pixels or analytics (don't reveal traffic to competitors)
// MDX posts from /content/blog/
// Categories: shopify-growth | ai-content | social-strategy | behind-results | tools
// Each post: reading time, publish date, category tag, author ("The Team" — no names)
// Related posts: 3 algorithmically selected by category
// Email capture at bottom of each post (Mailchimp or similar — stub it)
// Affiliate links: wrapped in /go/[service] redirect (track + update without touching posts)
```

---

## STEP 6: TELEGRAM BOT

```python
# api/services/telegram_service.py

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

STAVARAI_TELEGRAM_ID = int(os.getenv("TELEGRAM_USER_ID"))

def is_stavarai(update: Update) -> bool:
    """Only respond to Stavarai. Silence for everyone else."""
    return update.effective_user.id == STAVARAI_TELEGRAM_ID

async def handle_voice(update: Update, context):
    """Transcribe voice → parse as command → execute → respond"""
    if not is_stavarai(update): return
    
    # Download voice file
    voice_file = await update.message.voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()
    
    # Transcribe with Whisper
    transcript = await whisper_transcribe(audio_bytes)
    
    # Parse intent
    intent, entity = parse_voice_command(transcript)
    
    # Execute via Hermes
    result = await hermes_execute(intent, entity, context={"client": entity})
    
    # Respond
    await update.message.reply_text(result.summary)

# Commands: /status /run /approve /score /brief /report /help
# All commands check is_stavarai() first — no response if not him
```

---

## STEP 7: META GLASSES (VISIONCLAW)

```bash
# Clone VisionClaw
git clone https://github.com/Intent-Lab/VisionClaw.git /opt/visionclaw
cd /opt/visionclaw

# Read their README and configure webhook
# Set webhook URL to: https://[your-vps]/api/voice/command
# Configure Stavarai's glasses to use VisionClaw endpoint
```

```python
# api/routers/voice.py

@router.post("/voice/command")
async def voice_command(payload: VoicePayload, auth=Depends(verify_token)):
    """
    Receives: { transcript: str, source: "telegram"|"glasses", confidence: float }
    Parses: intent + entity
    Executes: Hermes command
    Returns: { response: str, tts_url: str | None }
    """
    intent = parse_intent(payload.transcript)
    entity = extract_entity(payload.transcript, intent)
    
    result = await hermes_execute(intent=intent, entity=entity)
    
    # Generate TTS response for glasses
    tts_url = await generate_tts(result.summary) if payload.source == "glasses" else None
    
    return {"response": result.summary, "tts_url": tts_url}
```

---

## STEP 8: KARPATHY AUTORESEARCH LOOP (Adapted)

```python
# api/services/autoresearch.py
# Adapted from karpathy/autoresearch for social content A/B testing

"""
WHAT THIS DOES:
  Instead of training an ML model, we're optimizing content scoring weights.
  
  "train.py" equivalent = score_content(content_unit, weights) -> float
  "program.md" equivalent = research.md per client per niche  
  Fixed "budget" = 10 posts per experiment cycle (not 5min GPU)
  Ratchet = only keep weight changes that improve human approval rate
  
LOOP:
  1. Read research.md (current scoring weights + hypothesis)
  2. Propose weight change (agent reads outlier patterns)
  3. Score 10 posts with new weights
  4. Compare: did approval-correlated posts score higher?
  5. If yes: git commit weights, update research.md
  6. If no: git revert, note failure in research_log.md
  7. Loop (max 20 iterations per night)
  
STUCK DETECTION (from Karpathy):
  If 5 consecutive experiments fail → shift strategy
  (switch from weight tuning to hook pattern analysis)
  
ENDGAME:
  After 100+ experiments: switch from explore to exploit
  (only fine-tune best-performing weight configuration)
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def run_autoresearch_loop(client_id: str, max_iterations: int = 20):
    research_file = Path(f"research/{client_id}/research.md")
    log_file = Path(f"research/{client_id}/research_log.md")
    results_file = Path(f"research/{client_id}/autoresearch-results.tsv")
    
    baseline_approval_rate = await get_baseline_approval_rate(client_id)
    consecutive_failures = 0
    
    for iteration in range(max_iterations):
        # Agent proposes weight change
        proposal = await hermes_propose_experiment(research_file.read_text())
        
        # Run experiment (score 10 posts with new weights)
        experiment_result = await run_scoring_experiment(
            client_id=client_id,
            weights=proposal.new_weights,
            n_posts=10
        )
        
        # Compare against baseline
        if experiment_result.approval_correlation > baseline_approval_rate:
            # Improvement found — keep it
            await commit_weights(client_id, proposal.new_weights, experiment_result)
            update_research_md(research_file, proposal, experiment_result, accepted=True)
            baseline_approval_rate = experiment_result.approval_correlation
            consecutive_failures = 0
        else:
            # No improvement — revert
            update_research_md(research_file, proposal, experiment_result, accepted=False)
            log_failure(log_file, iteration, proposal, experiment_result)
            consecutive_failures += 1
        
        # Log to TSV (Karpathy pattern)
        append_results_tsv(results_file, iteration, proposal, experiment_result)
        
        # Stuck detection
        if consecutive_failures >= 5:
            await shift_strategy(client_id, research_file, log_file)
            consecutive_failures = 0
        
        await asyncio.sleep(60)  # 1 min between experiments
```

---

## STEP 9: LANDING PAGE — FULL PAGE HERO

Build this as a standalone Next.js page at `/`.

**Design spec (Steve Krug + frontend-design skill):**
- Background: `#0C0E14` (true dark, not Bootstrap black)
- Signature element: animated counter of posts scheduled "right now" (fake but credible)
- Typography: `font-family: 'Geist', 'Plus Jakarta Sans', system-ui`
- ONE focus per section. One idea. One sentence.
- CTA button: dark background, single white text, no gradient, no shadow
- No stock photos. No generic "team of smiling people" photos.
- Hero section must be 100vh minimum

**Pain points sections (write like a person, not a marketer):**

```
Section 1: "You're scaling faster than you can hire."
  Body: The average agency grows 3 clients per month.
        The average content manager handles 4–6 accounts.
        The math doesn't work. Something breaks. Usually quality.

Section 2: "Your content looks like everyone else's."
  Body: AI tools give everyone the same hooks. The same captions.
        The same generic "are you struggling with X?" opener.
        Your brand deserves better than the median.

Section 3: "You have no idea which posts are actually working."
  Body: Reach and impressions aren't revenue.
        You need to know what's driving clicks, saves, and sales.
        Most agencies don't. Now you can.

Section 4: "Your competitors are moving faster."
  Body: They're not smarter. They've just systematized.
        The teams winning right now aren't the best creatives.
        They're the best at running volume without losing quality.
```

---

## STEP 10: DEPLOY TO VERCEL

```bash
# Link to Stavarai's Vercel account
npx vercel login
npx vercel link  # select or create project

# Set environment variables
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add DEMO_PASSWORD production  # BLASTER2026
vercel env add API_URL production  # VPS FastAPI URL

# Deploy
npm run build  # must pass 0 errors
vercel deploy --prod

# Verify:
# / → landing page renders
# /admin → password gate renders
# /admin + BLASTER2026 → dashboard renders with Stavarai greeting
# /blog → blog index renders
# /blog/[any-slug] → post renders
```

---

## SECURITY CHECKLIST (before any demo)

```
[ ] BLASTER2026 not logged anywhere (no console.log, no analytics)
[ ] All API keys encrypted at rest (Rust AES-256)
[ ] Supabase RLS enabled on all public tables
[ ] Schema isolation verified (client A cannot read schema_client_b)
[ ] Telegram bot ignores all non-Stavarai user IDs
[ ] VisionClaw endpoint requires valid session token
[ ] Rate limiting active on all routes (Rust)
[ ] No real client data in demo seeds
[ ] All error messages generic (no stack traces to users)
[ ] HTTPS only (Vercel enforces this)
[ ] No open CORS (API only accepts Vercel URL + localhost)
[ ] Supabase service key NOT in frontend code
[ ] Environment variables not committed to git (.env in .gitignore)
```

---

## GAPS TO FILL (identified before handoff)

### GAP 1: Stavarai's Supabase project ref
**Need:** SUPABASE_PROJECT_REF to run `supabase link`
**Action:** Ask Stavarai for this before Step 4

### GAP 2: Stavarai's Vercel project ID
**Need:** VERCEL_PROJECT_ID for deploy step
**Action:** Ask Stavarai, or create during `vercel link`

### GAP 3: Telegram Bot Token
**Need:** Register bot via BotFather, get token
**Action:** Walk Stavarai through BotFather setup
**Guide:**
  1. Open Telegram → search @BotFather
  2. Send /newbot
  3. Name: [pick internal name — NOT "Stavarai Platform" or "Buffer Blaster"]
  4. Username: something unmemorable to outsiders
  5. Copy token → add to .env as TELEGRAM_BOT_TOKEN
  6. Add Stavarai's Telegram user ID as TELEGRAM_USER_ID

### GAP 4: VisionClaw Configuration
**Need:** Meta glasses setup + VisionClaw config file
**Action:** Follow Intent-Lab/VisionClaw README with VPS webhook URL

### GAP 5: Firecrawl API Key
**Need:** firecrawl.dev account
**Action:** Stavarai signs up, adds API key to settings

### GAP 6: Blog post content (first 10 posts)
**Need:** Hermes writes drafts, Stavarai approves
**Action:** After platform is deployed, run: `hermes run --skill=blog-writer --count=10`
These become the first blog posts Stavarai reviews and publishes.

### GAP 7: Company-specific training data
**Need:** Actual client content history for autoresearch loop
**Action:** Export existing content performance data → load into Supabase
Until then: autoresearch loop runs on competitor outlier data as proxy

---

## WHAT GOOD LOOKS LIKE (Definition of Done)

```
LANDING PAGE:
  [ ] Full-page hero renders on mobile + desktop
  [ ] Pain points speak to agency owners, not tech buyers
  [ ] Blog section shows 3 real posts
  [ ] CTA leads somewhere (email or contact)
  [ ] Lighthouse score: Performance ≥ 90, Accessibility ≥ 95

ADMIN DASHBOARD:
  [ ] BLASTER2026 password gate works
  [ ] Stavarai greeting appears on first login
  [ ] 7-step onboarding overlay works and can be reset
  [ ] All 6 sidebar sections render
  [ ] Settings tab saves and masks API keys
  [ ] At least one demo client shows content in approval queue

HERMES:
  [ ] hermes status shows 7 skills loaded + Higgsfield MCP connected
  [ ] hermes run --client=demo-client completes without error
  [ ] Telegram /status returns real data
  [ ] Voice note in Telegram transcribes + executes command

BLOG:
  [ ] /blog renders index with 3+ posts
  [ ] /blog/[slug] renders individual post with correct metadata
  [ ] RSS feed at /blog/rss.xml works

SECURITY:
  [ ] All items in security checklist above: checked
  [ ] Penetration test: try to access /api/admin without token → 401
  [ ] Try wrong password 5 times → rate limited

DEPLOY:
  [ ] Vercel build: 0 errors, 0 warnings
  [ ] All routes return correct status codes
  [ ] No real client data visible anywhere
```

---

## FINAL NOTE TO CLAUDE CODE

This platform's success is measured by one thing:
The company Stavarai works for starts depending on the output.
Not the platform. The output.

Everything you build should be invisible to the company.
Stavarai and his partner see the engine.
Everyone else sees results.

Build accordingly.

---

*Begin with CLAUDE.md → 00_context/PROJECT.md → 02_specs/TDD_SPEC.md → Phase 1 implementation*
*Every test must FAIL before you implement. Every feature has a test.*
*Write a bead before every destructive operation.*
*When in doubt: simpler, faster, more private.*
