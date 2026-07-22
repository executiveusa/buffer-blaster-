# HANDOFF — Browser Agent → Finish Postatees Production Deploy

> **Read this entire document before taking any action.**
> You have SSH access to the Hostinger VPS and access to the Vercel account.
> Do not skip verification steps. Do not skip paste-backs. The owner is paying
> per token — be efficient, batch operations, and only ask when genuinely blocked.

---

## 0. Mission

**Take a partially-deployed Stavarai Platform from "broken v1" to "live in production" and verify it end-to-end.**

The platform is a private AI content-operations system for the Postatees brand (Stavarai = the owner's nephew). It consists of:
- A **Next.js frontend** (deployed to Vercel — your job to set up)
- A **FastAPI + Rust backend** (deployed to the VPS — partially done, broken)
- A **Supabase Postgres** (self-hosted on the same VPS)

The end state: a public Vercel URL showing the landing page, blog, and admin console; the admin console calling the live VPS API; `/api/health` returning `core=rust` + `platform=stavarai`.

---

## 1. Current state (verified as of writing)

### Repository
- **URL:** `https://github.com/executiveusa/buffer-blaster-.git`
- **Branch:** `main` at commit `0f4e0bf`
- **Status:** clean. Tests pass (46/46 pytest + Rust crate tests). Frontend builds with zero errors (22 routes).

### VPS (Hostinger, `31.220.58.212`)
- Ubuntu 24.04.3 LTS, 8GB RAM, 2 cores
- Already running: full self-hosted Supabase stack (`supabase-db`, Kong on `:8001`, Supavisor on `:5434`, Studio on `:3001`)
- **Already running:** `postatees` Linux user, Rust 1.97.1, `/home/postatees/stavarai-platform/` clone, venv, Rust core built
- **Broken v1 service:** `postatees-stavarai-api.service` is restart-looping because port `:8002` was already taken by another docker service (cascadia-brain)
- **DB collision:** v1 migrations tried to write to `public.clients`, which is cascadia-brain's table (different schema). Failed silently.

### Vercel
- Owner has a Vercel account. Not yet connected to this repo.
- 3 Vercel tokens exist in the vault (`VERCEL_TOKEN`, `VERCEL_TOKEN_2`, `VERCEL_TOKEN_3`)

### Credentials
- All secrets live in `E:\THE PAULI FILES\Cosmos_Vault.env` on the owner's Windows machine. **Read it once, extract only what's needed, do not paste the full file into any context.**
- The Supabase service-role key for the self-hosted stack is also discoverable on the VPS via `find /opt /root -maxdepth 6 -name '.env' -path '*supabase*'` (grep for `SUPABASE_SERVICE_ROLE_KEY`).

---

## 2. Architecture (target state)

```
Browser ──HTTPS──► <project>.vercel.app   (Next.js, Vercel)
                       │
                       └─HTTPS──► api.<domain>  ── OR ── HTTP ──► 31.220.58.212:<free-port>
                                      (Caddy TLS)                    (FastAPI + Rust on VPS)
                                                                        │
                                                                        └─► 127.0.0.1:8001 (Supabase Kong)
                                                                                │
                                                                                └─► supabase-db (Postgres)
                                                                                       │
                                                                                       └─► postatees_stavarai schema (our tables)
```

**Two operating modes** (do not break this toggle):
- `NEXT_PUBLIC_DEMO_MODE=true` → frontend renders with seeded data, no API calls (use this if API TLS isn't ready)
- `NEXT_PUBLIC_DEMO_MODE=false` + `NEXT_PUBLIC_API_URL=<api-url>` → frontend calls the VPS API

---

## 3. Step-by-step plan (do these in order)

### STEP 1 — Run the v2 mega-script on the VPS (one command, ~2 min)

This is the fix for both v1 problems. SSH to the VPS and run:

```bash
wget -qO- https://raw.githubusercontent.com/executiveusa/buffer-blaster-/main/scripts/deploy-postatees-full.sh | bash
```

The script does (all idempotent):
1. Stops the broken `postatees-stavarai-api` service
2. Syncs the repo to latest (`0f4e0bf`)
3. Probes for a free port in 8101-8150 range
4. Creates the `postatees_stavarai` Postgres schema (no more collision with `public.*`)
5. Builds the Rust core (already built from v1 — will skip fast)
6. Installs Python deps (already installed — will skip)
7. Writes `.env` with the probed port + auto-fills the Supabase service key
8. Installs the systemd unit with the probed port, starts it, verifies `/api/health`

**Verify after running:** The script ends with a green box. Inside it you'll see:
```
API:     http://31.220.58.212:<PORT>/api/health
```
Note that `<PORT>` — you need it for Step 4.

**Failure mode:** If `cargo test` fails or the service won't start, **stop**. Paste the last 30 lines of `/root/postatees-deploy.log` back to the owner. Do not push past a real error.

### STEP 2 — Confirm `/api/health` returns OUR response

From the VPS:
```bash
curl -s http://127.0.0.1:<PORT>/api/health | python3 -m json.tool
```

**Expected response:**
```json
{
    "status": "ok",
    "version": "1.0.0",
    "platform": "stavarai",
    "core": "rust",
    "time": "2026-..."
}
```

**Critical checks:**
- `platform` MUST be `"stavarai"` (if it says `"cascadia"` you're hitting the wrong service — wrong port)
- `core` MUST be `"rust"` (if it says `"python"` the prebuilt lib didn't load — check `/home/postatees/stavarai-platform/rust_core/native/libstavarai_core.so` exists)

If either is wrong, do not proceed. Diagnose first.

### STEP 3 — Confirm the API is reachable from the public internet

From your browser agent's machine (not the VPS):
```bash
curl -s http://31.220.58.212:<PORT>/api/health
```

If this times out, the Hostinger firewall is blocking the port. On the VPS:
```bash
ufw status
ufw allow <PORT>/tcp
```

Re-test from outside.

### STEP 4 — Deploy the frontend to Vercel

**Two paths — pick based on what's available:**

#### Path A — Vercel CLI (if `vercel` is installed and a token works)

On any machine with the repo (or the VPS itself):
```bash
cd /home/postatees/stavarai-platform  # or wherever the repo is
export VERCEL_TOKEN=<one-of-the-tokens-from-the-vault>
bash scripts/deploy-frontend-vercel.sh
```

The script creates the project, sets env vars, deploys. Captures the URL from output.

#### Path B — Vercel Dashboard (if CLI auth is fiddly)

1. Go to `https://vercel.com/new`
2. Import `executiveusa/buffer-blaster-`
3. **Configure Project:**
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`  ← CRITICAL
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `.next` (auto-detected)
4. **Environment Variables** (add all 3 EXACTLY):
   ```
   NEXT_PUBLIC_DEMO_MODE    = false
   NEXT_PUBLIC_API_URL      = http://31.220.58.212:<PORT>   ← the port from Step 1
   DEMO_PASSWORD            = BLASTER2026
   ```
5. Click **Deploy**. Wait ~2 minutes for the build.

**Capture the URL** — Vercel gives you `https://<project-name>.vercel.app` (and optionally `https://<project-name>-<hash>-<owner>.vercel.app`).

### STEP 5 — Verify the deployed frontend (open in browser)

Visit each URL below. Expected behavior:

| URL | Expected |
|---|---|
| `https://<project>.vercel.app/` | Landing page renders. Hero: "Your social feed, actually full." Pain points section with stats (11pm, 3×, $0, 14 days). How it works (3 steps). Results (47, 84, 4, 2). Footer with Blog + Sign in links. |
| `https://<project>.vercel.app/blog` | Blog index. Featured post at top. 6 more posts below. Categories: Shopify Growth, AI & Content, Social Strategy, Behind the Results, Tools. |
| `https://<project>.vercel.app/blog/product-descriptions-that-convert` (or any post) | Full post renders. Title, category badge, date, reading time, author "By The Team". Markdown body styled. |
| `https://<project>.vercel.app/admin` | Password gate. Single input. Enter `BLASTER2026` → redirects to `/admin/dashboard`. |
| `https://<project>.vercel.app/admin/dashboard` | "Welcome back, Stavarai." greeting. 4 stat cards (Active clients, Posts this week, Pending approval, Pipeline). Client table below. 7-step onboarding overlay on first visit. |
| `https://<project>.vercel.app/admin/settings` | 6 tabs: AI Providers, Integrations, Agent Config, MCP Servers, Voice Control, API Guide. Keys show as "not set" (they live on the VPS, not the frontend — that's correct). |
| `https://<project>.vercel.app/api/...` | (should 404 — Next.js doesn't proxy `/api` to the VPS automatically) |

### STEP 6 — Handle the mixed-content issue (likely needed)

Because the Vercel frontend is HTTPS and the VPS API is HTTP, **Chrome/Firefox will block the dashboard's API calls**. The admin dashboard may show "Loading…" forever or fail to fetch clients.

**Three fixes — do the cheapest one that unblocks the demo:**

#### Fix A — Flip to demo mode (fastest, makes dashboard work without API)
In Vercel dashboard → Project → Settings → Environment Variables:
- Change `NEXT_PUBLIC_DEMO_MODE` from `false` to `true`
- Redeploy (Deployments → ⋯ → Redeploy)

Dashboard now renders with seeded data. Loses live API connection but the demo works. **Use this for an owner demo tonight.**

#### Fix B — Cloudflare Tunnel (free HTTPS for the API, ~10 min setup)
1. On the VPS: `cloudflared tunnel --url http://localhost:<PORT>`
2. Captures a `https://<random>.trycloudflare.com` URL
3. Update Vercel env: `NEXT_PUBLIC_API_URL=https://<random>.trycloudflare.com`
4. Redeploy frontend

API now has HTTPS. Dashboard calls work. Good for a stable demo.

#### Fix C — Buy a domain + Caddy config (production-correct)
- Buy domain (Namecheap/Cloudflare/Porkbun, ~$10/yr)
- Point DNS A record at `31.220.58.212`
- Add Caddy site block for `api.<domain>` proxying to `127.0.0.1:<PORT>`
- Caddy auto-provisions Let's Encrypt TLS
- Update Vercel env: `NEXT_PUBLIC_API_URL=https://api.<domain>`
- Redeploy

**For tonight, do Fix A. Plan Fix C for the real launch.**

### STEP 7 — Write the deploy bead + report

On the VPS:
```bash
cat > /root/buffer-blaster/.beads/$(date -u +%Y%m%d)_production_live.bead << EOF
timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
action: production-live
scope: vps,vercel
description: |
  Stavarai Platform live in production for Postatees brand.
  - VPS API: http://31.220.58.212:<PORT>/api/health (core=rust, platform=stavarai)
  - Frontend: <VERCEL_URL>
  - DB schema: postatees_stavarai (isolated from public.*)
  - Mode: <demo|production>
verification:
  - /api/health returns core=rust + platform=stavarai
  - Frontend landing, blog, admin all render at <VERCEL_URL>
reversible: true
rollback:
  - Vercel: instant rollback in dashboard
  - VPS: systemctl stop postatees-stavarai-api; docker exec supabase-db psql -U postgres -d postgres -c 'DROP SCHEMA postatees_stavarai CASCADE;'
EOF
```

Also write a zero-context handoff at `ops/reports/production-live.json` per the GRINIONS format.

---

## 4. Verification URLs (paste these back to the owner)

After all steps, gather and paste back:

```
API health:        http://31.220.58.212:<PORT>/api/health
                   (response: {"status":"ok","core":"rust","platform":"stavarai",...})

Frontend landing:  https://<project>.vercel.app/
Frontend blog:     https://<project>.vercel.app/blog
Frontend admin:    https://<project>.vercel.app/admin  (password: BLASTER2026)

Service status:    systemctl status postatees-stavarai-api  (active)
DB schema check:   docker exec supabase-db psql -U postgres -d postgres -c '\dt postatees_stavarai.*'
                   (should list 10 tables)
```

---

## 5. What NOT to do (guardrails)

1. **Never paste `.env` contents or vault contents back to the owner.** Show only masked keys (last 4 chars).
2. **Never edit `public.*` tables.** They belong to cascadia-brain. Our stuff lives in `postatees_stavarai.*`.
3. **Never restart or stop the existing Supabase stack.** Other brands depend on it. Only operate on `postatees-stavarai-api` and the `postatees_stavarai` schema.
4. **Never deploy to Vercel with `NEXT_PUBLIC_DEMO_MODE=false` and an HTTP API URL** unless you've also set up API HTTPS (Fix B or C above). Mixed content will silently break the dashboard.
5. **Never expose internal names publicly.** The landing page and blog must NOT contain "stavarai", "hermes", "buffer blaster", or "higgsfield" anywhere in the rendered HTML. Grep the built `.next` if unsure.
6. **Never use port 8002.** It's taken by cascadia-brain's docker-proxy.
7. **If anything fails that you can't diagnose in 2 commands, stop.** Paste the relevant log section back. Do not thrash.

---

## 6. If you get stuck

- `/root/postatees-deploy.log` — full v2 deploy log
- `/var/log/postatees-stavarai-api.log` — FastAPI runtime log
- `systemctl status postatees-stavarai-api` — service state
- `docker exec supabase-db psql -U postgres -d postgres -c '\dt postatees_stavarai.*'` — confirms our schema
- `journalctl -u postatees-stavarai-api --no-pager | tail -50` — systemd journal

For Vercel issues: `vercel inspect <deployment-url>` or the Vercel dashboard's Build Logs.

---

## 7. Definition of done

- [ ] v2 mega-script ran clean, picked a free port, started service
- [ ] `curl http://31.220.58.212:<PORT>/api/health` returns `core=rust` + `platform=stavarai`
- [ ] Port is open externally (curl works from outside the VPS)
- [ ] Vercel project deployed, frontend URL live
- [ ] All 5 verification URLs from §4 render correctly
- [ ] Mixed-content issue resolved (one of Fix A/B/C applied)
- [ ] Bead written, report in `ops/reports/`
- [ ] Owner has the Vercel URL in chat

**When all 8 boxes are checked, paste the §4 verification block back to the owner and you're done.**

---

## 8. Context references (read if you need background)

- `docs/HANDOFF.md` — the original GPT-5.6 Sol handoff (full architecture + phase plan)
- `docs/POSTATEES_DEPLOY.md` — the v1 runbook (now superseded by the v2 mega-script, but useful background)
- `EMERALD_TABLETS.md` — non-negotiables (Tier 1-5)
- `AGENTS.md` — operating contract
- `openspec/changes/add-production-bringup/` — the accepted change spec driving this work

**Begin at Step 1. Don't ask permission between successful steps — keep going until done or genuinely blocked.**
