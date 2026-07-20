#!/usr/bin/env bash
# Prints the service-role key for the self-hosted Supabase on this VPS.
# The vault file has placeholders; the real key lives in the Supabase
# docker-compose .env on the box. This finds it.
set -euo pipefail

# Common locations for the self-hosted Supabase .env
CANDIDATES=(
  "/opt/supabase/docker/.env"
  "/opt/supabase/.env"
  "/root/supabase/docker/.env"
  "/srv/supabase/docker/.env"
)

found=0
for f in "${CANDIDATES[@]}"; do
  if [ -f "$f" ]; then
    echo "# found: $f"
    # Print only the service-role-related entries, mask everything else
    grep -E '^(SUPABASE_SERVICE_ROLE_KEY|ANON_KEY|JWT_SECRET|POSTGRES_PASSWORD|API_EXTERNAL_URL|SUPABASE_URL)' "$f" 2>/dev/null || true
    found=1
  fi
done

if [ "$found" = "0" ]; then
  echo "No Supabase .env found in common locations."
  echo "Look in /opt and /root for the supabase install:"
  echo "  find / -maxdepth 5 -name '.env' -path '*supabase*' 2>/dev/null"
  exit 1
fi
