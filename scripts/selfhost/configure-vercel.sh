#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DOMAIN="${API_DOMAIN:-}"
VERCEL_PROJECT_NAME="${VERCEL_PROJECT_NAME:-buffer-blaster}"
VERCEL_SCOPE="${VERCEL_SCOPE:-the-pauli-effect}"
SITE_URL="${SITE_URL:-https://buffer-blaster.vercel.app}"

usage() {
  cat <<'EOF'
Configure the canonical Buffer Blaster Vercel frontend for a live self-hosted backend.

Usage:
  VERCEL_TOKEN=... scripts/selfhost/configure-vercel.sh --domain api.example.com

Public live-mode values plus the server-only proxy-signing secret are written by
this script. Provider/API credentials remain on the VPS. Stripe server-side
secrets, if needed by a Vercel route, must be added separately as non-NEXT_PUBLIC
variables.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) API_DOMAIN="${2:-}"; shift 2 ;;
    --project) VERCEL_PROJECT_NAME="${2:-}"; shift 2 ;;
    --scope) VERCEL_SCOPE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

: "${API_DOMAIN:?--domain is required}"
: "${VERCEL_TOKEN:?VERCEL_TOKEN must be supplied in the environment}"

ENV_FILE="${BUFFER_BLASTER_ENV_FILE:-$ROOT/.env.production}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE is required so the frontend receives the same proxy-signing secret as the backend." >&2
  exit 2
fi

read_private_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true
}

PROXY_SHARED_SECRET="$(read_private_env BLASTER_PROXY_SHARED_SECRET)"
if [[ -z "$PROXY_SHARED_SECRET" ]]; then
  echo "ERROR: BLASTER_PROXY_SHARED_SECRET is missing from $ENV_FILE. Run the backend installer first." >&2
  exit 2
fi

cd "$ROOT/frontend"

VERCEL=(npx --yes vercel@latest --token "$VERCEL_TOKEN" --scope "$VERCEL_SCOPE")
"${VERCEL[@]}" link --yes --project "$VERCEL_PROJECT_NAME" >/dev/null

set_var() {
  local name="$1" value="$2"
  if printf '%s' "$value" | "${VERCEL[@]}" env update "$name" production >/dev/null 2>&1; then
    echo "updated $name"
  else
    printf '%s' "$value" | "${VERCEL[@]}" env add "$name" production >/dev/null
    echo "added $name"
  fi
}

set_var NEXT_PUBLIC_DEMO_MODE false
set_var NEXT_PUBLIC_PUBLIC_CONSOLE false
set_var NEXT_PUBLIC_API_URL "https://${API_DOMAIN}"
set_var SITE_URL "$SITE_URL"
set_var BLASTER_PROXY_SHARED_SECRET "$PROXY_SHARED_SECRET"

echo "Deploying canonical Buffer Blaster production frontend..."
"${VERCEL[@]}" deploy --prod --yes

echo
cat <<EOF
Vercel live-mode configuration submitted.
Project: $VERCEL_PROJECT_NAME
Frontend: $SITE_URL/studio
Backend: https://$API_DOMAIN
Proxy signing: configured server-side

Verify the deployment is READY and run the VPS smoke test before beta users enter.
EOF
