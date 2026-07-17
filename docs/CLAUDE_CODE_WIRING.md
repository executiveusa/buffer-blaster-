# CLAUDE CODE WIRING PROMPT
# Paste this into Claude Code to wire Buffer Blaster to your VPS.
# Requires: Claude Code installed, VPS SSH access, env vars ready.

---

## WHAT THIS DOES

This prompt sets up Buffer Blaster end-to-end on your VPS:
1. Clones the repo and installs dependencies
2. Sets up Supabase schema
3. Deploys Hermes agent with Buffer Blaster config
4. Sets up the agentic flywheel for self-improvement
5. Configures the mcp2cli bridge for Higgsfield CLI calls
6. Sets up the cron job for Airtable sync
7. Deploys frontend to Vercel (provide project ID)
8. Confirms everything is connected

---

## STEP-BY-STEP WIRING

Open Claude Code, connect to your VPS, paste this prompt:

```
You are setting up Buffer Blaster on my VPS. The repo is github.com/executiveusa/buffer-blaster-.
Follow these steps exactly. Do not skip steps. Write a bead checkpoint after each major step.

STEP 1: Environment check
- Verify Node.js >= 20, Python >= 3.11, git, Docker are installed
- If any missing, install via apt-get
- Check available disk (need >= 20GB)
- Check RAM (recommend >= 8GB for 50-parallel jobs)

STEP 2: Clone and install
```bash
git clone https://github.com/executiveusa/buffer-blaster-.git /opt/buffer-blaster
cd /opt/buffer-blaster
npm install
pip install -r requirements.txt --break-system-packages
```

STEP 3: Environment setup
Create /opt/buffer-blaster/.env with these vars (prompt me for each value):
- BUFFER_ACCESS_TOKEN
- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- HIGGSFIELD_API_KEY
- AIRTABLE_API_KEY
- AIRTABLE_BASE_ID=AIRTABLE_BASE_ID_PLACEHOLDER
- APIFY_API_TOKEN
- SHOPIFY_ADMIN_API_KEY
- HERMES_PROFILE=buffer-blaster
- ANTHROPIC_API_KEY
- VERCEL_PROJECT_ID=[I will provide this]
- GITHUB_TOKEN
- GITHUB_REPO=executiveusa/buffer-blaster-

STEP 4: Supabase schema
Run: npx supabase db push --db-url $SUPABASE_URL
Apply: supabase/migrations/001_initial_schema.sql

STEP 5: Install Hermes Agent
```bash
cd /opt
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
npm install
cp /opt/buffer-blaster/agents/orchestrator/hermes_config.yaml ~/.hermes/config.yaml
cp /opt/buffer-blaster/agents/orchestrator/SOUL.md ~/.hermes/SOUL.md
```

STEP 6: Install Sandcastle
```bash
npm install -g sandcastle
cp /opt/buffer-blaster/scripts/*.ts ~/.sandcastle/workflows/
```

STEP 7: Install mcp2cli (Higgsfield CLI bridge)
```bash
cd /opt
git clone https://github.com/knowsuchagency/mcp2cli.git
cd mcp2cli
pip install -e . --break-system-packages
# Configure: mcp2cli config add higgsfield --url https://mcp.higgsfield.ai/mcp
```

STEP 8: Install absurd (task resilience)
```bash
pip install absurd --break-system-packages
# or: git clone https://github.com/earendil-works/absurd.git
```

STEP 9: Airtable sync + initial commit
```bash
cd /opt/buffer-blaster
python scripts/sync_airtable.py
```

STEP 10: Set up agentic flywheel
```bash
git clone https://github.com/Dicklesworthstone/agentic_coding_flywheel_setup.git /opt/flywheel
cd /opt/flywheel
# Follow ACFS setup: creates VPS monitoring, auto-PR, skill improvement loop
bash setup.sh --project=buffer-blaster --repo=executiveusa/buffer-blaster-
```

STEP 11: Deploy frontend to Vercel
```bash
cd /opt/buffer-blaster/frontend
npm install
npx vercel deploy --prod --project-id=$VERCEL_PROJECT_ID
```

STEP 12: Start Hermes orchestrator as daemon
```bash
pm2 start "hermes run" --name buffer-blaster-orchestrator
pm2 save
pm2 startup
```

STEP 13: Schedule Airtable sync (weekly)
```bash
echo "0 6 * * 1 cd /opt/buffer-blaster && python scripts/sync_airtable.py" | crontab -
```

STEP 14: Health check
Verify:
- Hermes process is running (pm2 status)
- Supabase connection works (query clients table)
- Higgsfield MCP reachable via mcp2cli
- Buffer API responds (GET /profiles.json)
- Vercel URL is live
- GitHub push works (test commit)

STEP 15: Write completion bead
Create .beads/[timestamp]_vps-setup-complete.bead
Push to main.

Report: list of every service running + URL for frontend.
```

---

## ENVIRONMENT VARIABLES CHECKLIST

Get these before running:

| Variable | Where to get it |
|----------|----------------|
| BUFFER_ACCESS_TOKEN | buffer.com → Settings → Apps → Access Token |
| SUPABASE_URL | supabase.com → Project Settings → API |
| SUPABASE_SERVICE_KEY | supabase.com → Project Settings → API → service_role key |
| HIGGSFIELD_API_KEY | higgsfield.ai → Account → API Keys |
| AIRTABLE_API_KEY | airtable.com → Account → Developer Hub → Personal Access Token |
| APIFY_API_TOKEN | apify.com → Settings → Integrations |
| SHOPIFY_ADMIN_API_KEY | Per-client: Shopify Admin → Apps → Private apps |
| ANTHROPIC_API_KEY | console.anthropic.com → API Keys |
| VERCEL_PROJECT_ID | You'll provide this later |
| GITHUB_TOKEN | github.com → Settings → Developer settings → Personal access tokens |

---

## AIRTABLE STUB (for future use)

The Airtable integration is implemented as a stub. It will not block the build.

What's stubbed:
- `scripts/sync_airtable.py` — fully implemented, runs independently
- `supabase/migrations/001_initial_schema.sql` — `airtable_assets` table exists
- `config/airtable.ts` — stub client, returns empty arrays if no API key

To activate: Set AIRTABLE_API_KEY + AIRTABLE_BASE_ID, run `sync_airtable.py`.

---

## TROUBLESHOOTING

**Hermes not spawning children:**
- Check `hermes_config.yaml` → `delegation.max_concurrent_children`
- Verify ANTHROPIC_API_KEY is set for leaf worker model calls

**Higgsfield MCP timeout:**
- Check `mcp2cli config show higgsfield`
- Verify API key at higgsfield.ai
- absurd will retry automatically — check logs in Supabase agent_logs

**Buffer API 403:**
- Token may be expired — regenerate at buffer.com
- Check profile IDs are correct for the client

**Airtable sync fails:**
- Verify base ID: `AIRTABLE_BASE_ID_PLACEHOLDER`
- Check table name (script tries "Images" then "Gallery")
- API token needs `data.records:read` scope

**Supabase RLS blocking writes:**
- Use service_role key (not anon key) for agent writes
- Anon key is for frontend read-only

**Vercel deployment fails:**
- Provide project ID (you mentioned this later)
- `npx vercel link` to connect existing project
