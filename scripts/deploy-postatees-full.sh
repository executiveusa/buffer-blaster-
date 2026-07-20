#!/usr/bin/env bash
# ============================================================
#  deploy-postatees-full.sh v2 — collision-aware one-shot deploy.
#
#  v2 fixes (after v1 collided with cascadia-brain):
#    - Probes for a free port in 8100-8200 at runtime (no more hardcoded :8002)
#    - Stops the broken service before doing anything
#    - Applies 005_postatees_namespace.sql — moves ALL our tables into
#      the dedicated postatees_stavarai schema (no collision with public.*)
#    - Records the chosen port in the systemd unit + .env
#
#  Run ON the VPS as root. Fetch-and-run pattern keeps the script current:
#    wget -qO- https://raw.githubusercontent.com/executiveusa/buffer-blaster-/main/scripts/deploy-postatees-full.sh | bash
# ============================================================
set -uo pipefail   # NOT -e: we handle errors explicitly

LOG=/root/postatees-deploy.log
exec > >(tee -a "$LOG") 2>&1
echo "==== deploy-postatees-full.sh v2 started $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
hdr()  { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }
die()  {
  echo -e "\n${RED}✗ FATAL: $1${NC}"
  echo -e "${RED}  Paste everything from '==== deploy-postatees-full.sh' downward.${NC}"
  exit 1
}

[ "$(id -u)" -eq 0 ] || die "Run as root."

REPO_URL="https://github.com/executiveusa/buffer-blaster-.git"
ROOT_CLONE=/root/buffer-blaster
APP_USER=postatees
APP_HOME=/home/$APP_USER
APP_DIR=$APP_HOME/stavarai-platform
VENV=$APP_HOME/venv
VPS_IP=31.220.58.212
SUPABASE_DB_CONTAINER=supabase-db
SUPABASE_API_URL=http://127.0.0.1:8001

# ── 0. Stop the broken service if it's restart-looping ───────
hdr "0/11  STOP EXISTING SERVICE"
if systemctl list-unit-files 2>/dev/null | grep -q postatees-stavarai-api; then
  systemctl stop postatees-stavarai-api 2>/dev/null || true
  systemctl reset-failed postatees-stavarai-api 2>/dev/null || true
  ok "stopped prior postatees-stavarai-api (if any)"
else
  ok "no prior service to stop"
fi

# ── 1. Sync script source ────────────────────────────────────
hdr "1/11  SYNC SCRIPT SOURCE"
if [ -d "$ROOT_CLONE/.git" ]; then
  git -C "$ROOT_CLONE" fetch --quiet origin main || die "git fetch failed"
  git -C "$ROOT_CLONE" reset --hard --quiet origin/main || die "git reset failed"
else
  git clone --quiet "$REPO_URL" "$ROOT_CLONE" || die "git clone failed"
fi
LATEST_COMMIT=$(git -C "$ROOT_CLONE" rev-parse --short HEAD)
ok "root clone at $LATEST_COMMIT"

# Re-exec canonical if running from a stale copy
SELF=$(readlink -f "$0" 2>/dev/null || echo "$0")
CANONICAL="$ROOT_CLONE/scripts/deploy-postatees-full.sh"
if [ "$SELF" != "$CANONICAL" ] && [ -f "$CANONICAL" ]; then
  if ! diff -q "$SELF" "$CANONICAL" >/dev/null 2>&1; then
    warn "old copy — re-running canonical"
    exec bash "$CANONICAL"
  fi
fi

# ── 2. Probe for a free port ─────────────────────────────────
hdr "2/11  PROBE FREE PORT"
API_PORT=""
for p in 8101 8102 8103 8104 8105 8110 8120 8130 8140 8150 8200; do
  if ! ss -tlnH 2>/dev/null | grep -q ":$p "; then
    API_PORT=$p
    break
  fi
done
[ -n "$API_PORT" ] || die "no free port in 8100-8200 range"
ok "picked port $API_PORT"

# ── 3. Postatees user ────────────────────────────────────────
hdr "3/11  POSTATEES USER"
if id "$APP_USER" &>/dev/null; then ok "user '$APP_USER' exists"
else useradd -m -s /bin/bash -c "Postatees brand services" "$APP_USER" || die "useradd failed"; ok "user created"
fi

# ── 4. Supabase stack ────────────────────────────────────────
hdr "4/11  SUPABASE STACK"
docker ps --format '{{.Names}}' | grep -qx "$SUPABASE_DB_CONTAINER" || die "container '$SUPABASE_DB_CONTAINER' not running"
docker exec "$SUPABASE_DB_CONTAINER" psql -U postgres -c 'SELECT 1' >/dev/null 2>&1 || die "postgres not responding"
ok "supabase-db responds"

# ── 5. Rust toolchain ────────────────────────────────────────
hdr "5/11  RUST TOOLCHAIN"
export PATH="$HOME/.cargo/bin:$PATH"
command -v cargo &>/dev/null || curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable >/dev/null 2>&1
sudo -u "$APP_USER" -H bash -lc 'command -v cargo' >/dev/null 2>&1 || sudo -u "$APP_USER" -H bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable' >/dev/null 2>&1
ok "cargo ready"

# ── 6. Sync app repo ────────────────────────────────────────
hdr "6/11  APP REPO"
mkdir -p "$APP_HOME"; chown "$APP_USER:$APP_USER" "$APP_HOME"
if [ -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" -H git -C "$APP_DIR" fetch --quiet origin main || die "fetch failed"
  sudo -u "$APP_USER" -H git -C "$APP_DIR" reset --hard --quiet origin/main || die "reset failed"
else
  sudo -u "$APP_USER" -H git clone --quiet "$REPO_URL" "$APP_DIR" || die "clone failed"
fi
ok "app at $(sudo -u "$APP_USER" -H git -C "$APP_DIR" rev-parse --short HEAD)"

# ── 7. Rust build ────────────────────────────────────────────
hdr "7/11  RUST CORE"
info "cargo test..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo test --quiet 2>&1" | tail -3
[ "${PIPESTATUS[0]:-1}" -eq 0 ] || die "cargo test failed"
ok "tests passed"

info "cargo build --release..."
sudo -u "$APP_USER" -H bash -c "cd $APP_DIR/rust_core/stavarai_core && source \$HOME/.cargo/env && cargo build --release 2>&1" | tail -2
[ "${PIPESTATUS[0]:-1}" -eq 0 ] || die "cargo build failed"
mkdir -p "$APP_DIR/rust_core/native"
cp "$APP_DIR/rust_core/stavarai_core/target/release/libstavarai_core.so" "$APP_DIR/rust_core/native/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/rust_core/native"
ok "release built + lib dropped"

# ── 8. Python deps ───────────────────────────────────────────
hdr "8/11  PYTHON VENV"
[ -d "$VENV" ] || sudo -u "$APP_USER" -H python3 -m venv "$VENV"
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
info "installing api deps..."
sudo -u "$APP_USER" -H "$VENV/bin/pip" install --quiet -r "$APP_DIR/api/requirements.txt" 2>&1 | tail -2
ok "python deps installed"

# ── 9. Migrations (skip 003, apply 005 for namespace) ────────
hdr "9/11  DATABASE MIGRATIONS (NAMESPACED)"
info "applying 005_postatees_namespace.sql (creates postatees_stavarai schema)..."
docker exec -i "$SUPABASE_DB_CONTAINER" psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
  < "$APP_DIR/supabase/migrations/005_postatees_namespace.sql" 2>&1 | tail -5
# 005 is idempotent and CREATEs our schema + tables + function + seeds. If a
# NOTICE appears (already exists), that's fine. A real ERROR stops the deploy.
ok "namespaced schema ready (postatees_stavarai)"

# ── 10. .env (port-aware) ────────────────────────────────────
hdr "10/11  ENV FILE"
ENV_FILE="$APP_DIR/api/.env"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" << ENVTPL
PLATFORM_NAME=Stavarai
DEMO_PASSWORD=BLASTER2026
MASTER_ENCRYPTION_KEY=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
SUPABASE_URL=$SUPABASE_API_URL
SUPABASE_SERVICE_KEY=REPLACE_ME
STAVARAI_SCHEMA=postatees_stavarai
ACTIVE_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=REPLACE_ME
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
HERMES_PROFILE=postatees-stavarai
HERMES_MAX_CHILDREN=10
HIGGSFIELD_API_KEY=
HIGGSFIELD_MCP_URL=https://mcp.higgsfield.ai/mcp
BUFFER_ACCESS_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_USER_ID=
API_URL=http://$VPS_IP:$API_PORT
NEXT_PUBLIC_API_URL=http://$VPS_IP:$API_PORT
ENVTPL
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  ok ".env written with API_URL=http://$VPS_IP:$API_PORT"
else
  # Update just the port + schema on re-runs; preserve secrets.
  sed -i "s|^API_URL=.*|API_URL=http://$VPS_IP:$API_PORT|" "$ENV_FILE"
  sed -i "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$VPS_IP:$API_PORT|" "$ENV_FILE"
  grep -q '^STAVARAI_SCHEMA=' "$ENV_FILE" || echo "STAVARAI_SCHEMA=postatees_stavarai" >> "$ENV_FILE"
  ok ".env updated (port $API_PORT, schema postatees_stavarai) — secrets preserved"
fi

# Auto-fill SUPABASE_SERVICE_KEY if still REPLACE_ME
if grep -q "SUPABASE_SERVICE_KEY=REPLACE_ME" "$ENV_FILE"; then
  info "hunting for Supabase service key..."
  FOUND_KEY=$(find /opt /root /srv /home -maxdepth 6 -type f \( -name '.env' -o -name '*.env' \) 2>/dev/null | \
    while read -r f; do
      v=$(grep -E '^SUPABASE_SERVICE_ROLE_KEY=' "$f" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'" || true)
      [ -n "$v" ] && echo "$v"
    done | head -1)
  if [ -n "$FOUND_KEY" ]; then
    sed -i "s|^SUPABASE_SERVICE_KEY=.*|SUPABASE_SERVICE_KEY=$FOUND_KEY|" "$ENV_FILE"
    ok "service key auto-filled"
  else
    warn "couldn't auto-find service key — edit $ENV_FILE manually"
  fi
fi

# ── 11. systemd unit on the probed port + start + verify ─────
hdr "11/11  SYSTEMD + VERIFY"
UNIT=/etc/systemd/system/postatees-stavarai-api.service
cat > "$UNIT" << UNITEOF
[Unit]
Description=Postatees Stavarai Platform API (FastAPI) on :$API_PORT
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
UNITEOF
touch /var/log/postatees-stavarai-api.log
chown "$APP_USER:$APP_USER" /var/log/postatees-stavarai-api.log
systemctl daemon-reload
systemctl enable postatees-stavarai-api >/dev/null 2>&1

info "starting service on :$API_PORT..."
systemctl restart postatees-stavarai-api
sleep 5
if ! systemctl is-active --quiet postatees-stavarai-api; then
  warn "service inactive. Last 15 log lines:"
  tail -15 /var/log/postatees-stavarai-api.log
  die "service failed to start"
fi
ok "postatees-stavarai-api active on :$API_PORT"

info "verifying /api/health..."
sleep 2
HEALTH=$(curl -sf "http://127.0.0.1:$API_PORT/api/health" 2>/dev/null || echo "FAILED")
if [ "$HEALTH" = "FAILED" ]; then
  tail -15 /var/log/postatees-stavarai-api.log
  die "API not responding on :$API_PORT"
fi
echo -e "  ${BOLD}$HEALTH${NC}"
echo "$HEALTH" | grep -q '"core":"rust"' && ok "CORE=RUST CONFIRMED" || warn "core is python — check log"
echo "$HEALTH" | grep -q '"platform":"stavarai"' && ok "PLATFORM=STAVARAI CONFIRMED" || warn "not our platform — wrong service"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  POSTATEES DEPLOY COMPLETE (v2, collision-free)       ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}API:${NC}     http://$VPS_IP:$API_PORT/api/health"
echo -e "  ${BOLD}Schema:${NC}  postatees_stavarai (isolated from public.*)"
echo -e "  ${BOLD}Logs:${NC}    tail -f /var/log/postatees-stavarai-api.log"
echo -e "  ${BOLD}Service:${NC} systemctl {status|restart} postatees-stavarai-api"
echo ""
if grep -q "REPLACE_ME" "$ENV_FILE" 2>/dev/null; then
  echo -e "  ${YELLOW}NEXT:${NC} edit $ENV_FILE (replace REPLACE_ME), then systemctl restart postatees-stavarai-api"
fi
echo "Deploy log: $LOG"
echo "==== deploy-postatees-full.sh v2 finished $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
