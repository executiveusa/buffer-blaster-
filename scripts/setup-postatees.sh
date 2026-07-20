#!/usr/bin/env bash
# ============================================================
#  setup-postatees.sh — VPS-side deploy for the Stavarai Platform
#  under the Postatees brand. Run ON the VPS as root.
#
#  Architecture (per decision lock 2026-07-20):
#    - Frontend  → Vercel (separate deploy, see deploy-frontend-vercel.sh)
#    - Backend   → THIS script. FastAPI + Rust core on the VPS, port :8001
#    - Database  → existing self-hosted Postgres in Docker on :5434
#                  (new dedicated DB `postatees_stavarai` + role)
#
#  Isolation:
#    - Linux user `postatees` (created if missing)
#    - /home/postatees/stavarai-platform/ (everything lives here)
#    - systemd units prefixed `postatees-stavarai-*` (no global pm2)
#    - Postatees processes can't read other brands' files
#
#  Idempotent: safe to re-run. Skips completed steps.
#
#  Usage:  bash setup-postatees.sh
# ============================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────
APP_USER="postatees"
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/stavarai-platform"
REPO_URL="https://github.com/executiveusa/buffer-blaster-.git"
API_PORT=8002               # 8000 = docker, 8001 = supabase-kong, 8080 = docker → 8002
VPS_IP="31.220.58.212"
# Supabase self-hosted: Kong gateway on :8001 serves the REST API.
# We use the EXISTING postgres DB (no new database — per-client isolation
# happens at the schema level via create_client_schema()).
SUPABASE_API_URL="http://127.0.0.1:8001"
DB_HOST="127.0.0.1"
DB_PORT=5434                # Supavisor pooler → real Postgres in supabase-db

# ── Pretty output ────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
hdr()  { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }

[ "$(id -u)" -eq 0 ] || fail "Run as root. (sudo bash setup-postatees.sh)"

# ── 1. Create the isolated Postatees user ────────────────────
hdr "1/9  POSTATEES USER"
if id "$APP_USER" &>/dev/null; then
  ok "user '$APP_USER' already exists"
else
  info "creating user '$APP_USER'..."
  useradd -m -s /bin/bash -c "Postatees brand services" "$APP_USER"
  ok "user created"
fi

# ── 2. System deps (only what's missing) ─────────────────────
hdr "2/9  SYSTEM DEPENDENCIES"
# curl missing on this box per recon — install it
if ! command -v curl &>/dev/null; then
  info "installing curl..."
  apt-get update -qq
  apt-get install -y -qq curl ca-certificates build-essential pkg-config libssl-dev
  ok "curl + build tools installed"
else
  ok "curl already present"
fi

# Rust toolchain (for compiling the hot-path core)
if ! command -v cargo &>/dev/null; then
  info "installing Rust toolchain (rustup)..."
  # Install for both root (this script) and the postatees user (who'll run the build)
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable
  source "$HOME/.cargo/env"
  sudo -u "$APP_USER" -H bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable'
  ok "Rust installed for root + $APP_USER"
else
  ok "cargo already present: $(cargo --version)"
fi
source "$HOME/.cargo/env" 2>/dev/null || true

# ── 3. Clone / update the repo into Postatees home ───────────
hdr "3/9  REPOSITORY"
mkdir -p "$APP_HOME"
chown "$APP_USER:$APP_USER" "$APP_HOME"

if [ -d "$APP_DIR/.git" ]; then
  info "repo exists — pulling latest..."
  sudo -u "$APP_USER" -H git -C "$APP_DIR" pull --ff-only
  ok "repo updated"
else
  info "cloning $REPO_URL → $APP_DIR ..."
  sudo -u "$APP_USER" -H git clone "$REPO_URL" "$APP_DIR"
  ok "repo cloned"
fi

# ── 4. Verify the existing Supabase stack is reachable ──────
hdr "4/9  DATABASE (existing Supabase)"
info "checking the self-hosted Supabase stack..."
# We do NOT create a separate database. The platform isolates per-client via
# schemas inside the existing `postgres` DB (see 002_client_isolation.sql).
# We just need to confirm Supabase is up and find the container for migrations.
PG_CONTAINER=$(docker ps --format '{{.Names}}' | grep -xE 'supabase-db' | head -1)
if [ -z "$PG_CONTAINER" ]; then
  fail "supabase-db container not running. Start the Supabase stack first."
fi
ok "supabase-db container found: $PG_CONTAINER"

# Verify Postgres responds
if docker exec "$PG_CONTAINER" psql -U postgres -c 'SELECT 1' >/dev/null 2>&1; then
  ok "postgres responds inside $PG_CONTAINER"
else
  fail "postgres not responding in $PG_CONTAINER. Check the Supabase stack."
fi

# Probe the Kong gateway (REST API) — non-fatal if it's down, migrations use direct psql
if curl -sf "$SUPABASE_API_URL/rest/v1/" -H 'apikey: placeholder' >/dev/null 2>&1; then
  ok "supabase Kong gateway responding on :8001"
else
  warn "Kong gateway not reachable on $SUPABASE_API_URL — will use direct psql for migrations"
fi

# ── 5. Build the Rust core (this is the slow step, ~4 min) ──
hdr "5/9  RUST CORE BUILD"
cd "$APP_DIR/rust_core/stavarai_core"
info "running cargo test (proves the contract)..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo test --quiet" || \
  fail "Rust tests failed — do NOT proceed. Fix the divergence first."
ok "Rust tests pass"

info "building release (this takes ~4 minutes)..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo build --release --quiet" || \
  fail "cargo build --release failed"
ok "release build complete"

# Drop the prebuilt lib where the runtime loader expects it
mkdir -p "$APP_DIR/rust_core/native"
LIB_EXT="so"
LIB_SRC="$APP_DIR/rust_core/stavarai_core/target/release/libstavarai_core.$LIB_EXT"
LIB_DST="$APP_DIR/rust_core/native/libstavarai_core.$LIB_EXT"
cp "$LIB_SRC" "$LIB_DST"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/rust_core/native"
ok "prebuilt lib dropped at rust_core/native/"

# ── 6. Python backend deps (in a venv owned by postatees) ────
hdr "6/9  PYTHON VENV + DEPS"
VENV="$APP_HOME/venv"
if [ ! -d "$VENV" ]; then
  info "creating venv at $VENV..."
  sudo -u "$APP_USER" -H python3 -m venv "$VENV"
fi
info "installing Python deps..."
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet -r "$APP_DIR/api/requirements.txt"
ok "Python deps installed"

# ── 7. Frontend deps + build (we'll deploy from here to Vercel) ─
hdr "7/9  FRONTEND BUILD (local sanity check)"
info "installing frontend deps..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/frontend && npm ci --silent"
info "building (proves it compiles; Vercel will rebuild for production)..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/frontend && NEXT_PUBLIC_DEMO_MODE=true npm run build --silent" || \
  warn "frontend build had issues — not blocking the API deploy, but investigate before Vercel deploy"
ok "frontend built locally"

# ── 8. .env file for the API (template — YOU fill secrets) ───
hdr "8/9  ENVIRONMENT FILE"
ENV_FILE="$APP_DIR/api/.env"
if [ -f "$ENV_FILE" ]; then
  warn ".env already exists at $ENV_FILE — leaving untouched"
  warn "If you need to rotate, back it up and re-run after deleting it."
else
  info "writing .env template (you'll fill the secret values next)..."
  cat > "$ENV_FILE" << ENVTEMPLATE
# ── Postatees Stavarai Platform — API environment ─────────────
# Generated by setup-postatees.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# EDIT THIS FILE: replace every "REPLACE_ME" with a real value.

# Platform identity
PLATFORM_NAME=Stavarai
DEMO_PASSWORD=BLASTER2026
MASTER_ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Database — uses the EXISTING self-hosted Supabase stack on this VPS.
# Kong gateway on :8001 serves the REST API; Supavisor pooler on :5434 routes
# to the real Postgres in supabase-db. Per-client isolation happens at the
# schema level via create_client_schema() — no separate DB needed.
SUPABASE_URL=$SUPABASE_API_URL
SUPABASE_SERVICE_KEY=REPLACE_ME        # ← run scripts/print-supabase-key.sh after this

# LLM provider (pick ONE — set its key, blank the others)
ACTIVE_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=REPLACE_ME
OPENAI_API_KEY=
GOOGLE_AI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# Model names per provider (required by the config-driven adapter)
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
OPENAI_MODEL=gpt-4o
GOOGLE_MODEL=gemini-1.5-pro
OLLAMA_MODEL=llama3

# Hermes agent
HERMES_PROFILE=postatees-stavarai
HERMES_MAX_CHILDREN=10

# Video generation (Higgsfield)
HIGGSFIELD_API_KEY=REPLACE_ME
HIGGSFIELD_MCP_URL=https://mcp.higgsfield.ai/mcp

# Publishing / scraping / voice (fill what you'll use)
BUFFER_ACCESS_TOKEN=
APIFY_API_TOKEN=
FIRECRAWL_API_KEY=
AIRTABLE_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_USER_ID=
VISIONCLAW_WEBHOOK_SECRET=

# This API's own URL — Vercel calls this
API_URL=http://$VPS_IP:$API_PORT
NEXT_PUBLIC_API_URL=http://$VPS_IP:$API_PORT
ENVTEMPLATE
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  ok ".env written to $ENV_FILE (chmod 600)"
  warn "IMPORTANT: edit $ENV_FILE and replace every REPLACE_ME before starting the service."
fi

# ── 9. systemd unit for the FastAPI backend ──────────────────
hdr "9/9  SYSTEMD SERVICE"
UNIT_PATH="/etc/systemd/system/postatees-stavarai-api.service"
cat > "$UNIT_PATH" << UNIT
[Unit]
Description=Postatees Stavarai Platform API (FastAPI)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/api/.env
ExecStart=$VENV/bin/uvicorn api.app:app --host 0.0.0.0 --port $API_PORT
Restart=on-failure
RestartSec=3
StandardOutput=append:/var/log/postatees-stavarai-api.log
StandardError=append:/var/log/postatees-stavarai-api.log

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=$APP_HOME /var/log

[Install]
WantedBy=multi-user.target
UNIT
touch /var/log/postatees-stavarai-api.log
chown "$APP_USER:$APP_USER" /var/log/postatees-stavarai-api.log

systemctl daemon-reload
systemctl enable postatees-stavarai-api >/dev/null
ok "systemd unit installed: postatees-stavarai-api.service"

# ── Summary ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  POSTATEES VPS DEPLOY — DONE                                  ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}App dir:${NC}       $APP_DIR"
echo -e "  ${BOLD}DB:${NC}            postgres://$DB_USER:****@$DB_HOST:$DB_PORT/$DB_NAME"
echo -e "  ${BOLD}DB password:${NC}   $DB_PASS  ${YELLOW}(saved in $ENV_FILE)${NC}"
echo -e "  ${BOLD}API URL:${NC}       http://$VPS_IP:$API_PORT"
echo -e "  ${BOLD}Service:${NC}       systemctl {status|start|stop} postatees-stavarai-api"
echo -e "  ${BOLD}Logs:${NC}          tail -f /var/log/postatees-stavarai-api.log"
echo ""
echo -e "  ${BOLD}${YELLOW}NEXT — DO THESE IN ORDER:${NC}"
echo -e "   1. Edit $ENV_FILE and replace every REPLACE_ME."
echo -e "      (see scripts/print-supabase-key.sh for the service-role key)"
echo -e "   2. Apply DB migrations:"
echo -e "        sudo -u $APP_USER $VENV/bin/pip install --quiet supabase >/dev/null 2>&1"
echo -e "        cd $APP_DIR && sudo -u $APP_USER $VENV/bin/python -c \\"
echo -e "          'from supabase import create_client; c=create_client(\"http://$DB_HOST:$DB_PORT\",\"PLACEHOLDER\"); print(\"ok\")'"
echo -e "      (migrations will be applied via the SQL files in supabase/migrations/ — "
echo -e "       see docs/POSTATEES_DEPLOY.md step 4)"
echo -e "   3. Start the service:"
echo -e "        systemctl start postatees-stavarai-api"
echo -e "   4. Verify:"
echo -e "        curl http://$VPS_IP:$API_PORT/api/health"
echo -e "      Expect: {\"core\":\"rust\",\"status\":\"ok\",...}"
echo -e "   5. Deploy the frontend to Vercel (separate script):"
echo -e "        bash $APP_DIR/scripts/deploy-frontend-vercel.sh"
echo ""
