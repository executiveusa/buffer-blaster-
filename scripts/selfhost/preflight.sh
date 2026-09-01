#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE does not exist. Copy .env.production.example first." >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

missing_core=()
missing_integrations=()

require_core() {
  local key="$1"
  [[ -n "${!key:-}" ]] || missing_core+=("$key")
}
require_integration() {
  local key="$1"
  [[ -n "${!key:-}" ]] || missing_integrations+=("$key")
}

for key in API_DOMAIN MASTER_ENCRYPTION_KEY DEMO_PASSWORD BLASTER_API_KEY REDIS_URL; do
  require_core "$key"
done

for key in BUFFER_BLASTER_WORKSPACE_ID SUPABASE_DOCKER_NETWORK SUPABASE_URL SUPABASE_SERVICE_KEY OPENAI_API_KEY FAL_KEY FAL_TEXT_VIDEO_MODEL FAL_IMAGE_VIDEO_MODEL; do
  require_integration "$key"
done

if (( ${#missing_core[@]} > 0 )); then
  echo "CORE NOT READY — missing: ${missing_core[*]}" >&2
  exit 1
fi

echo "CORE CONFIG READY"

health_ok=false
if command -v curl >/dev/null 2>&1; then
  if curl --fail --silent --show-error --max-time 10 "https://${API_DOMAIN}/api/health" >/tmp/buffer-blaster-health.json 2>/tmp/buffer-blaster-health.err; then
    python3 - <<'PY'
import json
with open('/tmp/buffer-blaster-health.json', encoding='utf-8') as f:
    body = json.load(f)
assert body.get('status') == 'ok', body
print('PUBLIC HEALTH READY:', body.get('service'), '| core:', body.get('core'))
PY
    health_ok=true
  else
    echo "PUBLIC HEALTH PENDING — DNS/TLS may still be propagating or the service is not reachable yet."
  fi
fi
rm -f /tmp/buffer-blaster-health.json /tmp/buffer-blaster-health.err

if (( ${#missing_integrations[@]} > 0 )); then
  echo "INTEGRATIONS PENDING — add privately: ${missing_integrations[*]}"
  echo "BETA NOT READY"
  exit 0
fi

case "${SUPABASE_URL}" in
  *supabase.co*)
    echo "SELF-HOSTED SUPABASE NOT READY — SUPABASE_URL still targets managed Supabase." >&2
    exit 1
    ;;
  http://127.0.0.1:*|https://127.0.0.1:*|http://localhost:*|https://localhost:*)
    echo "SELF-HOSTED SUPABASE NOT READY — API runs in Docker; SUPABASE_URL must use a container/network-reachable hostname, not localhost." >&2
    exit 1
    ;;
esac

if command -v docker >/dev/null 2>&1; then
  if ! docker network inspect "${SUPABASE_DOCKER_NETWORK}" >/dev/null 2>&1; then
    echo "SELF-HOSTED SUPABASE NOT READY — Docker network '${SUPABASE_DOCKER_NETWORK}' not found." >&2
    exit 1
  fi

  if docker compose -f "$ROOT/docker-compose.prod.yml" ps --services --status running 2>/dev/null | grep -qx api; then
    if docker compose -f "$ROOT/docker-compose.prod.yml" exec -T api python - <<'PY'
import os
import urllib.request

url = os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/'
key = os.environ['SUPABASE_SERVICE_KEY']
req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
with urllib.request.urlopen(req, timeout=8) as response:
    if response.status < 200 or response.status >= 300:
        raise SystemExit(f'unexpected status {response.status}')
print('SELF-HOSTED SUPABASE ROUTE READY')
PY
    then
      :
    else
      echo "SELF-HOSTED SUPABASE NOT READY — API container cannot authenticate to PostgREST through SUPABASE_URL." >&2
      exit 1
    fi
  else
    echo "SELF-HOSTED SUPABASE ROUTE PENDING — API container is not running yet."
  fi
fi

if [[ "$health_ok" == true ]]; then
  echo "BETA CONFIG READY — run scripts/selfhost/smoke.sh before enabling the live frontend."
else
  echo "BETA CONFIG COMPLETE; public health proof is still pending."
fi
