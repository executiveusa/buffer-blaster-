# SECRETS.md — Environment Variable Structure
# ICM Stage: 00_context | NEVER commit with real values

## WHERE SECRETS LIVE
- Local dev: .env (gitignored)
- VPS: /opt/stavarai-platform/.env (chmod 600)
- Vercel: Vercel Environment Variables (encrypted at rest)
- Supabase: vault.secrets table (AES-256 via Rust core)

## MASTER ENV STRUCTURE

### Identity
PLATFORM_NAME=Stavarai             # Stavarai's name for greeting
DEMO_PASSWORD=BLASTER2026          # Admin gate — change after demo
MASTER_ENCRYPTION_KEY=             # 32-byte key for AES-256 (generate: openssl rand -hex 32)

### Supabase (Stavarai's account)
SUPABASE_URL=                      # From: supabase.com → Project Settings → API
SUPABASE_SERVICE_KEY=              # service_role key — NEVER in frontend
SUPABASE_PROJECT_REF=              # For: supabase link
NEXT_PUBLIC_SUPABASE_URL=          # Same URL — safe for frontend
NEXT_PUBLIC_SUPABASE_ANON_KEY=     # anon key — read-only, safe for frontend

### AI Providers (model-agnostic — only one active at a time)
ACTIVE_LLM_PROVIDER=anthropic      # anthropic | openai | google | ollama
ANTHROPIC_API_KEY=                 # console.anthropic.com
OPENAI_API_KEY=                    # platform.openai.com
GOOGLE_AI_API_KEY=                 # aistudio.google.com
OLLAMA_BASE_URL=http://localhost:11434  # for local models

### Hermes Agent
HERMES_PROFILE=stavarai-platform
HERMES_MAX_CHILDREN=10             # concurrent client orchestrators

### Video Generation
HIGGSFIELD_API_KEY=                # higgsfield.ai → Account → API Keys
HIGGSFIELD_MCP_URL=https://mcp.higgsfield.ai/mcp

### Social Publishing
BUFFER_ACCESS_TOKEN=               # buffer.com → Settings → Apps

### Research & Scraping
APIFY_API_TOKEN=                   # apify.com → Settings → Integrations
FIRECRAWL_API_KEY=                 # firecrawl.dev → Dashboard

### Client Data
AIRTABLE_API_KEY=                  # airtable.com → Developer Hub → Personal tokens
AIRTABLE_BASE_ID=apptABTHZ91toPYKi # Gallery base

### Voice Control
TELEGRAM_BOT_TOKEN=                # From @BotFather
TELEGRAM_USER_ID=                  # Stavarai's Telegram user ID (integer)
VISIONCLAW_WEBHOOK_SECRET=         # Shared secret for VisionClaw webhook auth

### Email (for approval notifications)
EMAIL_PROVIDER=resend
EMAIL_API_KEY=                     # resend.com → API Keys
EMAIL_FROM=noreply@[domain]

### Deploy
VERCEL_TOKEN=                      # vercel.com → Settings → Tokens
VERCEL_PROJECT_ID=                 # Stavarai provides this
API_URL=https://[vps-ip]:8000      # FastAPI backend URL

### GitHub (for Airtable sync commits)
GITHUB_TOKEN=                      # github.com → Settings → PAT
GITHUB_REPO=executiveusa/buffer-blaster-

## HOW SECRETS ARE STORED IN SUPABASE

Table: public.settings (encrypted column)
Schema:
  key TEXT (setting name)
  value TEXT (AES-256-GCM encrypted value)
  masked TEXT (last 4 chars only, for display)
  updated_at TIMESTAMPTZ

All reads/writes go through Rust core:
  GET /api/admin/settings → Rust decrypts for display
  PUT /api/admin/settings → Rust encrypts before write
  API calls → Rust decrypts in-memory, never logged
