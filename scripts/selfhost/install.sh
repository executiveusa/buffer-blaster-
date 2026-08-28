#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/executiveusa/buffer-blaster-.git"
REF="main"
INSTALL_DIR="/opt/stavarai"
API_DOMAIN=""
ALLOWED_ORIGIN="https://stavarai-platform.vercel.app"

usage() {
  cat <<'EOF'
One-click Stavarai backend installer (Ubuntu/Debian).

Usage:
  install.sh --domain api.example.com [--origin https://stavarai-platform.vercel.app] [--install-dir /opt/stavarai] [--ref main]

The script installs Docker if needed, checks out the repo, creates .env.production,
generates app-owned secrets locally, starts FastAPI + Caddy, and runs a non-paid preflight.
Provider credentials are intentionally left blank for the operator to add privately.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) API_DOMAIN="${2:-}"; shift 2 ;;
    --origin) ALLOWED_ORIGIN="${2:-}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:-}"; shift 2 ;;
    --ref) REF="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$API_DOMAIN" ]]; then
  echo "ERROR: --domain is required (example: api.example.com)." >&2
  exit 2
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root or with sudo." >&2
  exit 2
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: this one-click installer currently supports Debian/Ubuntu hosts." >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git openssl

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker Engine..."
  curl -fsSL https://get.docker.com | sh
fi

systemctl enable --now docker >/dev/null 2>&1 || true
docker compose version >/dev/null

if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch --tags --prune origin
else
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

git -C "$INSTALL_DIR" fetch --tags --prune origin
if git -C "$INSTALL_DIR" rev-parse --verify "origin/$REF" >/dev/null 2>&1; then
  git -C "$INSTALL_DIR" checkout -B "$REF" "origin/$REF"
else
  git -C "$INSTALL_DIR" checkout --detach "$REF"
fi

cd "$INSTALL_DIR"

if [[ ! -f .env.production ]]; then
  cp .env.production.example .env.production
fi
chmod 600 .env.production

set_env() {
  local key="$1" value="$2" file=".env.production"
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*$|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

get_env() {
  local key="$1"
  grep -E "^${key}=" .env.production | tail -n1 | cut -d= -f2- || true
}

set_env API_DOMAIN "$API_DOMAIN"
set_env ALLOWED_ORIGINS "$ALLOWED_ORIGIN"
set_env SUPABASE_PROJECT_REF "${SUPABASE_PROJECT_REF:-cyxdevcjycmffhmwxojh}"

if [[ -z "$(get_env MASTER_ENCRYPTION_KEY)" ]]; then
  set_env MASTER_ENCRYPTION_KEY "$(openssl rand -hex 32)"
fi
if [[ -z "$(get_env BLASTER_API_KEY)" ]]; then
  set_env BLASTER_API_KEY "$(openssl rand -hex 32)"
fi
if [[ -z "$(get_env DEMO_PASSWORD)" ]]; then
  set_env DEMO_PASSWORD "$(openssl rand -hex 16)"
fi

chmod 600 .env.production

echo "Starting Stavarai API and HTTPS edge..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo
bash scripts/selfhost/preflight.sh || true

echo
cat <<EOF
Core self-host install finished.

Install directory: $INSTALL_DIR
Private config:    $INSTALL_DIR/.env.production
Health URL:        https://$API_DOMAIN/api/health

Next:
  1. Add provider secrets to .env.production (Supabase, OpenAI, Fal, TryPost).
  2. Run: cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml up -d
  3. Run: cd $INSTALL_DIR && bash scripts/selfhost/preflight.sh
  4. Point the Vercel frontend at https://$API_DOMAIN using scripts/selfhost/configure-vercel.sh.

No secret values were printed by this installer.
EOF
