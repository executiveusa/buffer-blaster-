#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${API_DOMAIN:?API_DOMAIN is required}"
: "${BLASTER_API_KEY:?BLASTER_API_KEY is required}"

BASE="https://${API_DOMAIN}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl --fail --silent --show-error --max-time 15 "$BASE/api/health" > "$TMP/health.json"
curl --fail --silent --show-error --max-time 15 \
  -H "x-api-key: $BLASTER_API_KEY" \
  "$BASE/api/studio/status" > "$TMP/status.json"

python3 - "$TMP/health.json" "$TMP/status.json" <<'PY'
import json, sys
health = json.load(open(sys.argv[1], encoding='utf-8'))
status = json.load(open(sys.argv[2], encoding='utf-8'))
assert health.get('status') == 'ok', health
assert health.get('approval_gate') is True, health
assert status.get('ok') is True, status
assert status.get('approval_gate') is True, status
publishing = status.get('publishing', {}); assert publishing.get('required_for_core') is False, status
print('PASS health | core:', health.get('core'))
print('PASS studio | publishing:', status.get('publishing'))
print('PASS public publishing remains approval-gated')
PY

echo "Smoke test made no paid generation request and created no social post."
