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

for key in SUPABASE_URL SUPABASE_SERVICE_KEY OPENAI_API_KEY FAL_KEY FAL_TEXT_VIDEO_MODEL FAL_IMAGE_VIDEO_MODEL TRYPOST_URL TRYPOST_API_KEY; do
  require_integration "$key"
done

if (( ${#missing_core[@]} > 0 )); then
  echo "CORE NOT READY — missing: ${missing_core[*]}" >&2
  exit 1
fi

echo "CORE CONFIG READY"

health_ok=false
if command -v curl >/dev/null 2>&1; then
  if curl --fail --silent --show-error --max-time 10 "https://${API_DOMAIN}/api/health" >/tmp/stavarai-health.json 2>/tmp/stavarai-health.err; then
    python3 - <<'PY'
import json
with open('/tmp/stavarai-health.json', encoding='utf-8') as f:
    body = json.load(f)
assert body.get('status') == 'ok', body
print('PUBLIC HEALTH READY:', body.get('service'), '| core:', body.get('core'))
PY
    health_ok=true
  else
    echo "PUBLIC HEALTH PENDING — DNS/TLS may still be propagating or the service is not reachable yet."
  fi
fi
rm -f /tmp/stavarai-health.json /tmp/stavarai-health.err

if (( ${#missing_integrations[@]} > 0 )); then
  echo "INTEGRATIONS PENDING — add privately: ${missing_integrations[*]}"
  echo "BETA NOT READY"
  exit 0
fi

if [[ "$health_ok" == true ]]; then
  echo "BETA CONFIG READY — run scripts/selfhost/smoke.sh before enabling the live frontend."
else
  echo "BETA CONFIG COMPLETE; public health proof is still pending."
fi
