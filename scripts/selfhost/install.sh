#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/executiveusa/buffer-blaster-.git"
REF="main"
# Keep the historical install directory as a compatibility path for existing VPS installs.
INSTALL_DIR="/opt/stavarai"
API_DOMAIN=""
ALLOWED_ORIGIN="https://buffer-blaster.vercel.app"
REDIS_URL_ARG=""

usage() {
  cat <<'EOFU'
One-click Buffer Blaster backend installer (Ubuntu/Debian).

Usage:
  install.sh --domain api.example.com [--origin https://buffer-blaster.vercel.app] [--install-dir /opt/stavarai] [--ref main] [--redis-url redis://...]

The script installs Docker if needed, checks out the repo, creates .env.production,
generates app-owned secrets locally, starts FastAPI + Caddy, and runs a non-paid preflight.
Provider credentials are intentionally left blank for the operator to add privately.
The historical /opt/stavarai path is retained only so existing installations remain upgradeable.
EOFU
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) API_DOMAIN="${2:-}"; shift 2 ;;
    --origin) ALLOWED_ORIGIN="${2:-}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:-}"; shift 2 ;;
    --ref) REF="${2:-}"; shift 2 ;;
    --redis-url) REDIS_URL_ARG="${2:-}"; shift 2 ;;
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
# A project ref is account-specific. Never silently bind a fresh install to a
# committed project identifier; preserve the current file unless explicitly supplied.
if [[ -n "${SUPABASE_PROJECT_REF:-}" ]]; then
  set_env SUPABASE_PROJECT_REF "$SUPABASE_PROJECT_REF"
fi

if [[ -z "$(get_env MASTER_ENCRYPTION_KEY)" ]]; then
  set_env MASTER_ENCRYPTION_KEY "$(openssl rand -hex 32)"
fi
if [[ -z "$(get_env BLASTER_API_KEY)" ]]; then
  set_env BLASTER_API_KEY "$(openssl rand -hex 32)"
fi
if [[ -z "$(get_env DEMO_PASSWORD)" ]]; then
  set_env DEMO_PASSWORD "$(openssl rand -hex 16)"
fi

if [[ -n "$REDIS_URL_ARG" ]]; then
  set_env REDIS_URL "$REDIS_URL_ARG"
elif [[ -z "$(get_env REDIS_URL)" ]]; then
  if [[ -z "$(get_env REDIS_PASSWORD)" ]]; then
    GENERATED_REDIS_PW="$(openssl rand -hex 24)"
    set_env REDIS_PASSWORD "$GENERATED_REDIS_PW"
    set_env REDIS_URL "redis://:${GENERATED_REDIS_PW}@redis:6379/0"
  else
    set_env REDIS_URL "redis://:$(get_env REDIS_PASSWORD)@redis:6379/0"
  fi
fi

chmod 600 .env.production

echo "Starting Buffer Blaster API and HTTPS edge..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo
bash scripts/selfhost/preflight.sh || true

echo
cat <<EOFFIN
Core self-host install finished.

Install directory: $INSTALL_DIR
Private config:    $INSTALL_DIR/.env.production

Next:
  1. Add provider secrets to .env.production (Supabase, OpenAI, Fal).
  2. Run: cd $INSTALL_DIR && docker compose -f docker-compose.prod.yml up -d
  3. Run: cd $INSTALL_DIR && bash scripts/selfhost/preflight.sh
  4. Point the Vercel frontend at https://$API_DOMAIN using scripts/selfhost/configure-vercel.sh.

No secret values were printed by this installer.
EOFFIN
