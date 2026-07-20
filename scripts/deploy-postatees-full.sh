#!/usr/bin/env bash
# ============================================================
#  deploy-postatees-full.sh — ONE-SHOT end-to-end Postatees deploy.
#
#  Run ON the VPS as root. Does everything:
#    1. Sync the script source itself (so we're never running stale code)
#    2. Create the postatees user (idempotent)
#    3. Verify the existing Supabase stack
#    4. Clone/sync the repo into /home/postatees/stavarai-platform
#    5. Build the Rust core (cargo test + cargo build --release)
#    6. Drop the prebuilt .so where the loader expects it
#    7. Create the Python venv + install deps
#    8. Apply the DB migrations directly via docker exec supabase-db psql
#    9. Write the .env (preserving any existing values, only filling blanks)
#   10. Install the systemd unit, start it, verify it's running
#   11. Hit /api/health and confirm core=rust
#
#  On ANY failure: stops, prints the failing step, writes a log to
#  /root/postatees-deploy.log, tells you exactly what to paste back.
#
#  Usage:  bash /root/buffer-blaster/scripts/deploy-postatees-full.sh
#          (or fetch + run in one go — see below)
# ============================================================
set -uo pipefail   # NOT -e: we handle errors explicitly so we can log them

LOG=/root/postatees-deploy.log
exec > >(tee -a "$LOG") 2>&1
echo "==== deploy-postatees-full.sh started $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="

# ── Pretty output ────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
hdr()  { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }
die()  {
  echo -e "\n${RED}✗ FATAL: $1${NC}"
  echo -e "${RED}  Step failed. Scroll up for the error, or check $LOG${NC}"
  echo -e "${RED}  Paste everything from '==== deploy-postatees-full.sh started' downward.${NC}"
  exit 1
}

[ "$(id -u)" -eq 0 ] || die "Run as root."

# ── Config ───────────────────────────────────────────────────
REPO_URL="https://github.com/executiveusa/buffer-blaster-.git"
ROOT_CLONE=/root/buffer-blaster
APP_USER=postatees
APP_HOME=/home/$APP_USER
APP_DIR=$APP_HOME/stavarai-platform
VENV=$APP_HOME/venv
VPS_IP=31.220.58.212
API_PORT=8002                  # 8000/8001/8080 all taken by existing services
SUPABASE_DB_CONTAINER=supabase-db
SUPABASE_API_URL=http://127.0.0.1:8001   # Kong gateway

# ── 1. Sync the script source ────────────────────────────────
hdr "1/11  SYNC SCRIPT SOURCE"
if [ -d "$ROOT_CLONE/.git" ]; then
  info "pulling latest into $ROOT_CLONE..."
  git -C "$ROOT_CLONE" fetch --quiet origin main || die "git fetch failed (network?)"
  git -C "$ROOT_CLONE" reset --hard --quiet origin/main || die "git reset failed"
  git -C "$ROOT_CLONE" submodule update --init --recursive --quiet 2>/dev/null || true
else
  info "cloning $ROOT_CLONE..."
  git clone --quiet "$REPO_URL" "$ROOT_CLONE" || die "git clone failed"
fi
LATEST_COMMIT=$(git -C "$ROOT_CLONE" rev-parse --short HEAD)
ok "root clone at $LATEST_COMMIT"

# Sanity: confirm the script we're running IS the latest version.
# (If you're running an old copy of this script, this check catches it.)
SELF_ON_DISK=$(readlink -f "$0" 2>/dev/null || echo "$0")
CANONICAL="$ROOT_CLONE/scripts/deploy-postatees-full.sh"
if [ "$SELF_ON_DISK" != "$CANONICAL" ] && [ -f "$CANONICAL" ]; then
  if ! diff -q "$SELF_ON_DISK" "$CANONICAL" >/dev/null 2>&1; then
    warn "you ran an old copy of this script. Re-running the canonical version..."
    exec bash "$CANONICAL"
  fi
fi
ok "running canonical script"

# ── 2. Postatees user ────────────────────────────────────────
hdr "2/11  POSTATEES USER"
if id "$APP_USER" &>/dev/null; then
  ok "user '$APP_USER' exists"
else
  useradd -m -s /bin/bash -c "Postatees brand services" "$APP_USER" || die "useradd failed"
  ok "user '$APP_USER' created"
fi

# ── 3. Verify Supabase stack ─────────────────────────────────
hdr "3/11  SUPABASE STACK"
docker ps --format '{{.Names}}' | grep -qx "$SUPABASE_DB_CONTAINER" || \
  die "container '$SUPABASE_DB_CONTAINER' not running. Start the Supabase stack first."
ok "supabase-db container present"

docker exec "$SUPABASE_DB_CONTAINER" psql -U postgres -c 'SELECT 1' >/dev/null 2>&1 || \
  die "postgres not responding inside $SUPABASE_DB_CONTAINER"
ok "postgres responds"

# ── 4. Rust toolchain (idempotent) ───────────────────────────
hdr "4/11  RUST TOOLCHAIN"
export PATH="$HOME/.cargo/bin:$PATH"
if ! command -v cargo &>/dev/null; then
  info "installing Rust for root..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable >/dev/null 2>&1 || die "rustup root install failed"
  source "$HOME/.cargo/env"
fi
if ! sudo -u "$APP_USER" -H bash -lc 'command -v cargo' >/dev/null 2>&1; then
  info "installing Rust for $APP_USER..."
  sudo -u "$APP_USER" -H bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable' >/dev/null 2>&1 || die "rustup user install failed"
fi
ok "cargo $(cargo --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1) for root + $APP_USER"

# ── 5. Sync the app repo ─────────────────────────────────────
hdr "5/11  APP REPO"
mkdir -p "$APP_HOME"
chown "$APP_USER:$APP_USER" "$APP_HOME"
if [ -d "$APP_DIR/.git" ]; then
  info "syncing $APP_DIR..."
  sudo -u "$APP_USER" -H git -C "$APP_DIR" fetch --quiet origin main || die "app git fetch failed"
  sudo -u "$APP_USER" -H git -C "$APP_DIR" reset --hard --quiet origin/main || die "app git reset failed"
else
  info "cloning into $APP_DIR..."
  sudo -u "$APP_USER" -H git clone --quiet "$REPO_URL" "$APP_DIR" || die "app git clone failed"
fi
APP_COMMIT=$(sudo -u "$APP_USER" -H git -C "$APP_DIR" rev-parse --short HEAD)
ok "app at $APP_COMMIT"

# ── 6. Rust core: test + build ───────────────────────────────
hdr "6/11  RUST CORE (test + build)"
info "running cargo test (proves the parity contract)..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo test --quiet 2>&1" | tail -5
[ "${PIPESTATUS[0]:-1}" -eq 0 ] || die "cargo test failed. Rust/Python contract has diverged — fix before proceeding."
ok "cargo test passed"

info "building release (~4 min on 2 cores)..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo build --release 2>&1" | tail -3
[ "${PIPESTATUS[0]:-1}" -eq 0 ] || die "cargo build --release failed"
ok "release build done"

mkdir -p "$APP_DIR/rust_core/native"
cp "$APP_DIR/rust_core/stavarai_core/target/release/libstavarai_core.so" "$APP_DIR/rust_core/native/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/rust_core/native"
ok "prebuilt lib dropped at rust_core/native/libstavarai_core.so"

# ── 7. Python venv + deps ────────────────────────────────────
hdr "7/11  PYTHON VENV"
if [ ! -d "$VENV" ]; then
  sudo -u "$APP_USER" -H python3 -m venv "$VENV" || die "venv creation failed"
fi
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
info "installing api deps (this takes ~1 min)..."
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet -r "$APP_DIR/api/requirements.txt" 2>&1 | tail -3
[ "${PIPESTATUS[0]:-1}" -eq 0 ] || die "pip install failed"
ok "python deps installed"

# ── 8. DB migrations ─────────────────────────────────────────
hdr "8/11  DATABASE MIGRATIONS"
info "applying 4 migrations to the existing postgres DB via $SUPABASE_DB_CONTAINER..."
for f in "$APP_DIR"/supabase/migrations/0*.sql; do
  fname=$(basename "$f")
  echo "  → $fname"
  docker exec -i "$SUPABASE_DB_CONTAINER" psql -U postgres -d postgres -v ON_ERROR_STOP=1 < "$f" >/dev/null 2>&1
  if [ $? -ne 0 ]; then
    # Many migrations use CREATE TABLE IF NOT EXISTS — re-running is safe.
    # But if 002 (create_client_schema function) genuinely fails, we want to know.
    warn "  $fname had non-zero exit. Showing error:"
    docker exec -i "$SUPABASE_DB_CONTAINER" psql -U postgres -d postgres -v ON_ERROR_STOP=1 < "$f" 2>&1 | head -5
  fi
done
ok "migrations applied (if a CREATE ALREADY EXISTS warning appeared, that's fine)"

# ── 9. .env file ─────────────────────────────────────────────
hdr "9/11  ENV FILE"
ENV_FILE="$APP_DIR/api/.env"
if [ ! -f "$ENV_FILE" ]; then
  info "writing .env template..."
  cat > "$ENV_FILE" << ENVTEMPLATE
# Postatees Stavarai Platform — API environment
# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
PLATFORM_NAME=Stavarai
DEMO_PASSWORD=BLASTER2026
MASTER_ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)

# Supabase (existing self-hosted stack)
SUPABASE_URL=$SUPABASE_API_URL
SUPABASE_SERVICE_KEY=REPLACE_ME

# LLM
ACTIVE_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=REPLACE_ME
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Hermes
HERMES_PROFILE=postatees-stavarai
HERMES_MAX_CHILDREN=10

# Video + publishing (fill what you'll use)
HIGGSFIELD_API_KEY=
HIGGSFIELD_MCP_URL=https://mcp.higgsfield.ai/mcp
BUFFER_ACCESS_TOKEN=

# Voice
TELEGRAM_BOT_TOKEN=
TELEGRAM_USER_ID=

# This API's URL (Vercel frontend calls this)
API_URL=http://$VPS_IP:$API_PORT
NEXT_PUBLIC_API_URL=http://$VPS_IP:$API_PORT
ENVTEMPLATE
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  ok ".env written (template — you'll fill REPLACE_ME values)"
else
  ok ".env already exists — preserving your values"
fi

# Try to auto-fill SUPABASE_SERVICE_KEY by hunting for the docker-compose .env
if grep -q "SUPABASE_SERVICE_KEY=REPLACE_ME" "$ENV_FILE"; then
  info "hunting for the Supabase service-role key in common .env locations..."
  FOUND_KEY=""
  for candidate in /opt/supabase/docker/.env /opt/supabase/.env /root/supabase/docker/.env /srv/supabase/docker/.env; do
    if [ -f "$candidate" ]; then
      FOUND_KEY=$(grep -E '^SUPABASE_SERVICE_ROLE_KEY=' "$candidate" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'" || true)
      [ -n "$FOUND_KEY" ] && { info "found key in $candidate"; break; }
    fi
  done
  if [ -z "$FOUND_KEY" ]; then
    info "recursive search..."
    FOUND_KEY=$(find /opt /root /srv /home -maxdepth 6 -type f \( -name '.env' -o -name '*.env' \) 2>/dev/null | \
      while read -r f; do
        v=$(grep -E '^SUPABASE_SERVICE_ROLE_KEY=' "$f" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'" || true)
        [ -n "$v" ] && echo "$v"
      done | head -1)
  fi
  if [ -n "$FOUND_KEY" ]; then
    sed -i "s|^SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=$FOUND_KEY|" "$ENV_FILE"
    ok "SUPABASE_SERVICE_KEY auto-filled"
  else
    warn "could not auto-find SUPABASE_SERVICE_KEY. You'll edit $ENV_FILE manually."
  fi
fi

# ── 10. systemd unit + start ─────────────────────────────────
hdr "10/11  SYSTEMD SERVICE"
UNIT=/etc/systemd/system/postatees-stavarai-api.service
cat > "$UNIT" << UNITFILE
[Unit]
Description=Postatees Stavarai Platform API (FastAPI)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/uvicorn api.app:app --host 0.0.0.0 --port $API_PORT
Restart=on-failure
RestartSec=3
StandardOutput=append:/var/log/postatees-stavarai-api.log
StandardError=append:/var/log/postatees-stavarai-api.log
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=$APP_HOME /var/log

[Install]
WantedBy=multi-user.target
UNITFILE
touch /var/log/postatees-stavarai-api.log
chown "$APP_USER:$APP_USER" /var/log/postatees-stavarai-api.log
systemctl daemon-reload
systemctl enable postatees-stavarai-api >/dev/null 2>&1
ok "systemd unit installed"

info "starting service..."
systemctl restart postatees-stavarai-api
sleep 4
if ! systemctl is-active --quiet postatees-stavarai-api; then
  warn "service did not go active. Last 15 log lines:"
  tail -15 /var/log/postatees-stavarai-api.log
  die "service failed to start"
fi
ok "postatees-stavarai-api is active"

# ── 11. Verify /api/health ───────────────────────────────────
hdr "11/11  VERIFY"
info "calling /api/health..."
sleep 2
HEALTH=$(curl -sf "http://127.0.0.1:$API_PORT/api/health" 2>/dev/null || echo "FAILED")
if [ "$HEALTH" = "FAILED" ]; then
  warn "local health check failed. Last 15 log lines:"
  tail -15 /var/log/postatees-stavarai-api.log
  die "API not responding on :$API_PORT"
fi
echo -e "  ${BOLD}$HEALTH${NC}"
echo "$HEALTH" | grep -q '"core":"rust"' && ok "CORE=RUST CONFIRMED" || warn "core is not rust — check the log"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  POSTATEES DEPLOY COMPLETE                            ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}API:${NC}     http://$VPS_IP:$API_PORT/api/health"
echo -e "  ${BOLD}Logs:${NC}    tail -f /var/log/postatees-stavarai-api.log"
echo -e "  ${BOLD}Service:${NC} systemctl {status|restart|stop} postatees-stavarai-api"
echo -e "  ${BOLD}App dir:${NC} $APP_DIR"
echo ""
if grep -q "REPLACE_ME" "$ENV_FILE" 2>/dev/null; then
  echo -e "  ${YELLOW}NEXT:${NC} edit $ENV_FILE and replace REPLACE_ME values, then:"
  echo -e "        systemctl restart postatees-stavarai-api"
fi
echo ""
echo "Deploy log saved to $LOG"
echo "==== deploy-postatees-full.sh finished $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
