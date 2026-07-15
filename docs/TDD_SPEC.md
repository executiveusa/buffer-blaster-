# TDD SPEC — Stavarai Platform
# ICM Stage: 02_specs | Tests before every line of implementation
# Version: 1.0.0

---

## SPEC FORMAT

Each feature follows:
```
FEATURE: [name]
STORY: As [who], I [what], so that [why]
GIVEN: [preconditions]
WHEN: [action]
THEN: [expected outcome]
TEST FILE: [03_tests/path/to/test_file]
STATUS: [ ] not started | [~] in progress | [✓] passing
```

---

## MODULE 1: AUTHENTICATION & ACCESS

### SPEC 1.1 — Demo Mode (No Auth)
```
FEATURE: Password-only demo access
STORY: As a demo user, I enter BLASTER2026, so I can see the platform without OAuth setup
GIVEN: Landing page is loaded
WHEN: User navigates to /admin
THEN: Password prompt appears — no email, no OAuth
WHEN: User enters "BLASTER2026"
THEN: Redirected to /admin/dashboard with Stavarai greeting
WHEN: User enters wrong password
THEN: Error shown, no redirect, no hint given
TEST FILE: 03_tests/auth/test_demo_auth.py
STATUS: [ ]
```

### SPEC 1.2 — Stavarai Personal Greeting
```
FEATURE: Named welcome + one-time onboarding overlay
STORY: As Stavarai, I see my name when I log in, so it feels like MY platform
GIVEN: First login to dashboard (or overlay manually reset in settings)
WHEN: Dashboard loads after auth
THEN: Full-screen overlay appears with: "Welcome back, Stavarai." + animated intro
THEN: 7-step walkthrough of platform features, one card at a time
THEN: "Got it" button dismisses overlay and sets localStorage flag
WHEN: Subsequent logins
THEN: No overlay — directly to dashboard
WHEN: Settings > "Reset Walkthrough" clicked
THEN: Flag cleared — overlay reappears next login
TEST FILE: 03_tests/auth/test_onboarding_overlay.ts
STATUS: [ ]
```

### SPEC 1.3 — Session Security
```
FEATURE: Rust-based session token validation
STORY: As the system, I validate all backend requests in Rust, so auth is fast + tamper-proof
GIVEN: A request arrives at any /api/admin/* route
WHEN: Authorization header is missing
THEN: 401 returned in <1ms (Rust middleware)
WHEN: Token is invalid or expired
THEN: 401 returned in <1ms
WHEN: Token is valid
THEN: Request passes to FastAPI handler
PERFORMANCE: Token validation < 1ms p99
TEST FILE: 03_tests/rust/test_auth_middleware.rs
STATUS: [ ]
```

---

## MODULE 2: CLIENT MANAGEMENT (ENTERPRISE ISOLATION)

### SPEC 2.1 — Client Onboarding
```
FEATURE: New client creates isolated Supabase schema
STORY: As Stavarai, I create a new client, so their data is isolated from all others
GIVEN: Admin is authenticated
WHEN: POST /api/admin/clients { name, niche, shopify_url }
THEN: New Supabase schema created: schema_{client_slug}
THEN: All 8 tables from buffer-blaster schema created in that schema
THEN: Client row written to public.clients master table
THEN: Client appears in dashboard client list
WHEN: Any query runs for this client
THEN: Connection uses schema_{client_slug} — NEVER public or another client schema
DATA ISOLATION: Verify with test that client A data cannot be read when authenticated as client B
TEST FILE: 03_tests/clients/test_client_isolation.py
STATUS: [ ]
```

### SPEC 2.2 — Shopify CSV Upload
```
FEATURE: LTV data ingestion per client
STORY: As Stavarai, I upload a Shopify CSV, so the scoring model has real customer data
GIVEN: Client exists, authenticated
WHEN: POST /api/admin/clients/{id}/shopify-csv with multipart file
THEN: CSV parsed (Python pandas)
THEN: Top 20% LTV customers identified
THEN: Segments written to schema_{slug}.customer_segments
THEN: Response: { total_customers, top_segment_count, avg_ltv, top_products[] }
WHEN: CSV has malformed rows
THEN: Skip malformed, process valid, report skip count
WHEN: File is not CSV
THEN: 422 Unprocessable Entity, no partial writes
TEST FILE: 03_tests/clients/test_shopify_csv.py
STATUS: [ ]
```

### SPEC 2.3 — Airtable Gallery Sync Per Client
```
FEATURE: Per-client Airtable image sync
STORY: As Stavarai, I sync a client's Airtable gallery, so videos reference their real assets
GIVEN: Client has airtable_base_id configured
WHEN: POST /api/admin/clients/{id}/sync-airtable
THEN: Python sync script runs async (absurd task)
THEN: Images downloaded to assets/{client_slug}/
THEN: Metadata written to schema_{slug}.airtable_assets
THEN: GitHub commit with message "sync: {client_name} gallery [{timestamp}]"
THEN: Webhook triggers Hermes to load new assets into next content run
TEST FILE: 03_tests/clients/test_airtable_sync.py
STATUS: [ ]
```

---

## MODULE 3: HERMES AGENT INTEGRATION

### SPEC 3.1 — Hermes Install + Skills Load
```
FEATURE: Hermes agent with Higgsfield skills pre-loaded
STORY: As the system, I install Hermes with all skills, so it runs the full pipeline
GIVEN: VPS with Node 20+, Hermes cloned
WHEN: npm run agent:install
THEN: Hermes installed at /opt/hermes
THEN: All SKILL.md files from skills/ copied to ~/.hermes/skills/
THEN: Higgsfield skills registered (food-beverage, ugc-video, scoring)
THEN: SOUL.md loaded as identity
THEN: hermes status returns: OK, 7 skills loaded, MCP: higgsfield connected
TEST FILE: 03_tests/agents/test_hermes_install.sh
STATUS: [ ]
```

### SPEC 3.2 — LLM Provider Adapter
```
FEATURE: Model-agnostic provider switching
STORY: As Stavarai, I change the LLM in settings, so I'm never locked to one provider
GIVEN: Settings tab is open
WHEN: Provider dropdown changed (Claude / GPT-4o / Gemini / local Ollama)
THEN: HERMES_MODEL env var updated
THEN: Next Hermes call uses new provider
THEN: No code changes required — adapter pattern
ADAPTERS REQUIRED:
  - anthropic (claude-sonnet-4-6 default)
  - openai (gpt-4o)
  - google (gemini-1.5-pro)
  - ollama (local — any model)
TEST FILE: 03_tests/agents/test_llm_adapter.py
STATUS: [ ]
```

### SPEC 3.3 — Pipeline Execution
```
FEATURE: End-to-end client content pipeline
STORY: As Stavarai, I trigger a pipeline run for a client, so content is generated autonomously
GIVEN: Client has completed interview, research data exists
WHEN: POST /api/admin/pipeline/{client_id}/run
THEN: Hermes spawns per-client child orchestrator
THEN: Child spawns: content-writer-leaf, video-prompter-leaf, scorer-leaf
THEN: Real-time status updates via Supabase realtime → dashboard
THEN: On completion: approval queue populated, email sent
PIPELINE TIMEOUT: 4 hours max (video generation)
ON FAILURE: absurd retry, bead written, Stavarai notified via Telegram
TEST FILE: 03_tests/pipeline/test_e2e_pipeline.py
STATUS: [ ]
```

### SPEC 3.4 — Karpathy Autoresearch Loop (Social A/B)
```
FEATURE: Autonomous A/B test loop for content optimization
STORY: As the system, I run content experiments overnight, so scoring improves automatically
MECHANISM (adapted from Karpathy autoresearch):
  - "train.py" equivalent = content scoring function
  - "program.md" equivalent = research.md per client per niche
  - Fixed "budget" = 10 posts per experiment cycle
  - Ratchet: only keep scoring weight changes that improve approval rate
  - Log all experiments to autoresearch-results.tsv per client
GIVEN: Client has 10+ published posts with approval data
WHEN: Nightly cron runs autoresearch loop at 2am
THEN: Agent reads research.md, proposes scoring weight changes
THEN: Runs "experiment" — scores 10 posts with new weights
THEN: Compares approval-correlated score vs. baseline
THEN: If improvement: git commit weights, write bead
THEN: If regression: git revert, note in research_log.md
TEST FILE: 03_tests/autoresearch/test_ab_loop.py
STATUS: [ ]
```

---

## MODULE 4: VOICE CONTROL (TELEGRAM + META GLASSES)

### SPEC 4.1 — Telegram Bot (BotFather Setup)
```
FEATURE: Hermes control via Telegram
STORY: As Stavarai, I send a voice message to my Telegram bot, so Hermes executes commands
GIVEN: Bot registered via BotFather, TELEGRAM_BOT_TOKEN set
COMMANDS:
  /status — Hermes status + active pipelines
  /run {client} — trigger pipeline for client
  /approve {queue_id} — approve queued content
  /score {content_id} — score a specific post
  /brief {client} — start grill-me interview in Telegram
  /report — weekly performance summary for all clients
  /help — command list
VOICE INPUT:
  User sends voice note → Whisper transcribes → parsed as command → executed
  Response sent as text (with Telegram formatting) + voice if configured
SECURITY:
  Bot only responds to Stavarai's Telegram user ID (configured in env)
  All other users get: no response (not even an error)
TEST FILE: 03_tests/telegram/test_bot_commands.py
STATUS: [ ]
```

### SPEC 4.2 — Meta Glasses (VisionClaw Integration)
```
FEATURE: Hermes control via Meta Ray-Ban Smart Glasses
STORY: As Stavarai, I speak to my glasses, so Hermes runs without me touching my phone
SOURCE: Intent-Lab/VisionClaw
GIVEN: VisionClaw configured with Hermes webhook URL
WHEN: Stavarai says "Hey platform, run pipeline for [client name]"
THEN: VisionClaw captures audio → Whisper transcribes
THEN: NLP parses: intent=run_pipeline, entity=client_name
THEN: POST /api/voice/command { transcript, intent, entity }
THEN: Hermes executes command
THEN: TTS response plays through glasses speaker
COMMANDS VIA VOICE:
  - "Run pipeline for [client]"
  - "What's the status?"
  - "Approve everything in [client]'s queue"
  - "Start interview for new client [name]"
  - "What are today's top posts?"
ACCESSIBILITY: Full platform control from glasses — no phone required
TEST FILE: 03_tests/voice/test_visionclaw_integration.py
STATUS: [ ]
```

---

## MODULE 5: DASHBOARD (TAILADMIN — STAVARAI ONLY)

### SPEC 5.1 — Dashboard Base (TailAdmin Customized)
```
FEATURE: Private admin dashboard — password protected
STACK: TailAdmin React (free, MIT, AI-ready) + Next.js 15 + Tailwind v4
CUSTOMIZATION:
  - All TailAdmin branding removed
  - Color scheme: deep charcoal (#0F1117) + electric indigo (#6366F1) accent
  - Logo: Stavarai's initials or custom mark
  - Sidebar: Clients | Pipelines | Content | Blog | Settings | Analytics
  - NO Buffer Blaster branding visible to anyone except Stavarai
ROUTES:
  /admin — password gate
  /admin/dashboard — overview metrics
  /admin/clients — client list + status
  /admin/clients/[slug] — per-client view
  /admin/pipeline — active pipeline runs
  /admin/content/[client] — content approval queue
  /admin/blog — blog post manager
  /admin/settings — API keys, LLM provider, agents
  /admin/analytics — scoring trends, approval rates
TEST FILE: 03_tests/dashboard/test_routes.ts
STATUS: [ ]
```

### SPEC 5.2 — Settings Tab
```
FEATURE: Full settings panel for API keys + agent config
STORY: As Stavarai, I manage all API keys in one place, so I never touch .env manually
SECTIONS:
  AI Providers:
    - Primary LLM (dropdown: Claude / GPT-4o / Gemini / Ollama)
    - API key field (masked, stored in Supabase encrypted column)
    - Test connection button
  
  Integrations:
    - Higgsfield API Key + "Test Higgsfield" button
    - Buffer Access Token + profile sync
    - Airtable API Key
    - Apify API Token
    - Firecrawl API Key (web scraping)
  
  Agent Config:
    - Hermes max concurrent children (slider: 1-50)
    - Video generation timeout (slider: 1-10 hours)
    - Auto-approve threshold (score ≥ X — default: off)
  
  MCP Servers:
    - Higgsfield MCP URL (pre-filled)
    - Shopify MCP URL (per-client)
    - Add custom MCP server button
  
  Voice Control:
    - Telegram Bot Token
    - Telegram User ID (Stavarai's)
    - VisionClaw webhook URL
    - TTS voice selection
  
  Required APIs Guide:
    - Small in-UI guide: "APIs you need and where to get them"
    - Link to each service's API key page
    - Green checkmark when key is validated

SECURITY: All keys encrypted with AES-256 (Rust) before Supabase write
TEST FILE: 03_tests/dashboard/test_settings.py
STATUS: [ ]
```

### SPEC 5.3 — Browser Use / Web Scraping
```
FEATURE: In-dashboard URL scanner + competitor scraper
STORY: As Stavarai, I paste a competitor URL, so Hermes analyzes it immediately
GIVEN: Settings has Firecrawl API key
WHEN: URL entered in "Scan URL" field on any client page
THEN: Firecrawl crawls URL, extracts: title, meta, key copy, social links
THEN: Hermes analyzes: what's their positioning? what hooks do they use?
THEN: Output shown in dashboard: competitor profile card
WHEN: "Find Competitors" clicked on a client
THEN: Apify scrapes top 5 competitors by niche + keyword
THEN: Each competitor analyzed and stored in schema_{slug}.research_runs
TEST FILE: 03_tests/dashboard/test_browser_use.py
STATUS: [ ]
```

---

## MODULE 6: LANDING PAGE (PUBLIC-FACING)

### SPEC 6.1 — Full-Page Hero
```
FEATURE: Public marketing landing page
STORY: As a company owner, I land on this page, so I feel understood and want to learn more
HERO:
  - Full-viewport height
  - Headline: speaks directly to the pain of a social media agency owner
  - NOT: "AI-powered content creation platform"
  - YES: "Your team is working 60-hour weeks. Your clients want more. AI doesn't sleep."
  - Sub-headline: one specific result (e.g., "3x content output. Same team size.")
  - Single CTA: "See how it works" → smooth scroll to demo section
  - Background: dark, cinematic — NOT tech-blue or startup-gradient
  - Typography: editorial, not corporate

PAIN POINTS ADDRESSED (sections below the hero):
  1. "You're scaling clients faster than you can hire"
  2. "Your content looks like everyone else's — because it is"
  3. "You have no idea which posts are actually driving revenue"
  4. "Your competitors are moving faster. You can feel it."

SOCIAL PROOF:
  - Results shown as specifics, not percentages
  - "47 posts scheduled in 2 hours" not "3x faster"
  
BLOG PREVIEW:
  - Latest 3 blog posts shown
  - CTA: "Read the playbook"

FOOTER:
  - Blog link
  - Admin login (subtle — small text)
  - No social links yet (they'd lead competitors to the platform)

TEST FILE: 03_tests/landing/test_landing_page.ts
STATUS: [ ]
```

### SPEC 6.2 — Demo Section
```
FEATURE: Live demo on landing page
STORY: As a company owner, I try a demo, so I believe this works before reaching out
DEMO MODE:
  - No login required
  - Show: seeded content calendar for a fake brand
  - Show: viral scoring in real time (animation)
  - Show: one piece of video content that was "generated" (pre-rendered demo)
  - CTA after demo: "Want this for your agency?" → mailto or contact form

WHAT THE DEMO NEVER SHOWS:
  - How it works
  - Buffer Blaster
  - Hermes
  - Any real client data

TEST FILE: 03_tests/landing/test_demo_section.ts
STATUS: [ ]
```

---

## MODULE 7: BLOG

### SPEC 7.1 — Blog Architecture
```
FEATURE: MDX-powered blog with affiliate hooks
STORY: As a potential client, I read the blog, so I trust Stavarai's team before hiring them
STACK: Next.js MDX + static generation + Vercel
URL STRUCTURE: /blog/[slug]
SEO: Full meta tags, OG images, JSON-LD schema, sitemap.xml, robots.txt
CATEGORIES:
  - shopify-growth (Shopify-specific tactics)
  - ai-content (AI content strategy, avoiding slop)
  - social-media-strategy (platform-specific playbooks)
  - behind-the-results (case studies, anonymized)
  - tools-we-use (affiliate opportunity)

FIRST 10 POSTS (Hermes writes draft, Stavarai approves):
  1. "Why Your Shopify Product Descriptions Are Invisible (And How to Fix It)"
  2. "The 3 TikTok Hook Patterns Driving 80% of CPG Sales Right Now"
  3. "AI Content Isn't the Problem. AI Slop Is."
  4. "How We Generated 47 Posts for 5 Clients in One Afternoon"
  5. "The Honest Guide to Pinterest for Beauty Brands"
  6. "What Actually Converts on Instagram Reels (It's Not What Brands Think)"
  7. "Before You Hire a Content Manager, Read This"
  8. "The Social Media Calendar Template We Actually Use"
  9. "Why Your Competitor's Content Outperforms Yours (Data-Backed)"
  10. "How to Make Your Shopify Store's Social Presence Feel Real"

AFFILIATE HOOKS (phase 2 — stub in code, activate later):
  - Shopify partner link
  - Buffer affiliate link
  - Higgsfield (if affiliate program exists)
  - Email platform affiliate (Klaviyo, etc.)

TEST FILE: 03_tests/blog/test_blog_routes.ts
STATUS: [ ]
```

---

## MODULE 8: RUST CORE

### SPEC 8.1 — AES-256 Encryption for API Keys
```
FEATURE: Encrypt sensitive data at rest
STORY: As the system, I encrypt all API keys with AES-256, so a DB breach exposes nothing
GIVEN: Rust encryption module compiled and linked
WHEN: POST /api/admin/settings with api_key field
THEN: Rust module encrypts key before write: encrypt(key, MASTER_KEY)
WHEN: GET /api/admin/settings
THEN: Rust module decrypts for display (masked): "sk-•••••••••[last4]"
WHEN: Key used in API call
THEN: Rust module decrypts in memory, key never logged
KEY ROTATION: Master key rotation invalidates all stored keys (force re-entry)
TEST FILE: 03_tests/rust/test_encryption.rs
STATUS: [ ]
```

### SPEC 8.2 — Rate Limiter
```
FEATURE: Per-route rate limiting in Rust
STORY: As the system, I rate-limit all API routes, so brute-force and abuse is blocked
LIMITS:
  POST /api/auth/verify: 5 req/minute per IP
  POST /api/admin/*: 100 req/minute per session
  POST /api/pipeline/*/run: 10 req/hour per client
  POST /api/voice/*: 60 req/minute
MECHANISM: Token bucket algorithm in Rust (no Redis dependency)
RESPONSE: 429 Too Many Requests with Retry-After header
TEST FILE: 03_tests/rust/test_rate_limiter.rs
STATUS: [ ]
```

### SPEC 8.3 — Job Queue
```
FEATURE: High-performance async job queue for pipeline tasks
STORY: As the system, I queue all long-running tasks, so the API never blocks
GIVEN: Any task expected to take > 2 seconds (video gen, scraping, scoring)
WHEN: Task submitted
THEN: Rust job queue accepts it (<1ms response)
THEN: Worker picks up task from queue
THEN: Status updates via Supabase realtime
THEN: Completion event triggers Hermes next step
PERSISTENCE: Queue state survives process restart
TEST FILE: 03_tests/rust/test_job_queue.rs
STATUS: [ ]
```

---

## MODULE 9: ACCESSIBILITY (arXiv Accessible HTML Standard)

### SPEC 9.1 — WCAG + arXiv HTML Compliance
```
FEATURE: Accessible HTML across all pages
STANDARD: https://info.arxiv.org/about/accessible_HTML.html
REQUIREMENTS:
  - All images have alt text
  - All forms have labels
  - Keyboard navigation works on all interactive elements
  - Color contrast ≥ 4.5:1 (WCAG AA) on all text
  - No information conveyed by color alone
  - Screen reader tested (NVDA + VoiceOver)
  - Focus visible on all interactive elements
  - ARIA roles correct on all dynamic content
  - Skip-to-content link on all pages
  - Language attribute on <html> tag
TESTING: Automated with axe-core + manual review
TEST FILE: 03_tests/accessibility/test_wcag.ts
STATUS: [ ]
```

---

## MODULE 10: DEPLOYMENT

### SPEC 10.1 — Vercel Frontend Deploy
```
FEATURE: One-command Vercel deploy for testing
GIVEN: Vercel project ID provided
WHEN: npm run deploy
THEN: Next.js builds successfully (0 errors)
THEN: Landing page live at [vercel-url]/
THEN: Admin gate live at [vercel-url]/admin
THEN: Blog live at [vercel-url]/blog
THEN: All Supabase env vars injected via Vercel env
TEST FILE: 03_tests/deploy/test_vercel_build.sh
STATUS: [ ]
```

### SPEC 10.2 — Local Development Mode
```
FEATURE: Full local dev with no cloud dependencies
STORY: As Stavarai, I run the full platform locally, so I can demo anywhere offline
WHEN: npm run dev:local
THEN: Next.js starts on localhost:3000
THEN: FastAPI starts on localhost:8000
THEN: Hermes agent starts in local mode
THEN: Supabase local starts (supabase start)
THEN: All features work without internet (except video gen)
TEST FILE: 03_tests/deploy/test_local_dev.sh
STATUS: [ ]
```

---

## IMPLEMENTATION ORDER (for Claude Code)

Execute specs in this order — do not skip ahead:

```
Phase 1 (Foundation):
  SPEC 1.1 → 1.2 → 1.3 (Auth)
  SPEC 2.1 (Client isolation)
  SPEC 8.1 → 8.2 → 8.3 (Rust core)

Phase 2 (Platform Core):
  SPEC 3.1 → 3.2 → 3.3 (Hermes)
  SPEC 5.1 → 5.2 → 5.3 (Dashboard)
  SPEC 2.2 → 2.3 (Data ingestion)

Phase 3 (Content Engine):
  SPEC 3.4 (Autoresearch loop)
  SPEC 9.1 (Accessibility)

Phase 4 (Voice + Mobile):
  SPEC 4.1 (Telegram)
  SPEC 4.2 (Meta Glasses)

Phase 5 (Public-Facing):
  SPEC 6.1 → 6.2 (Landing page)
  SPEC 7.1 (Blog)

Phase 6 (Deploy):
  SPEC 10.1 → 10.2 (Deploy)
```

---

*Write tests in 03_tests/ before implementing in 04_implementation/*
*Every test must FAIL first, then PASS after implementation — that's TDD*
