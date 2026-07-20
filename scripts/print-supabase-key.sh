#!/usr/bin/env bash
# Prints the service-role key for the self-hosted Supabase on this VPS.
# The vault file has placeholders; the real key lives in the Supabase
# docker-compose .env on the box. This finds it.
set -euo pipefail

echo "# Searching for the Supabase docker-compose .env..."
echo

# Common locations + a recursive search as fallback
CANDIDATES=(
  "/opt/supabase/docker/.env"
  "/opt/supabase/.env"
  "/root/supabase/docker/.env"
  "/srv/supabase/docker/.env"
  "/opt/supabase-auth/.env"
)

found=0
for f in "${CANDIDATES[@]}"; do
  if [ -f "$f" ]; then
    echo "# found: $f"
    grep -E '^(SUPABASE_SERVICE_ROLE_KEY|ANON_KEY|JWT_SECRET|POSTGRES_PASSWORD|API_EXTERNAL_URL|SUPABASE_URL|SITE_URL)' "$f" 2>/dev/null || true
    echo
    found=1
  fi
done

if [ "$found" = "0" ]; then
  echo "# No Supabase .env in common locations — running recursive search..."
  echo
  # Look for any .env that mentions the service role key pattern, anywhere likely
  find /opt /root /srv /home -maxdepth 6 -type f \( -name '.env' -o -name '*.env' \) 2>/dev/null | \
    while read -r f; do
      if grep -q 'SUPABASE_SERVICE_ROLE_KEY\|JWT_SECRET' "$f" 2>/dev/null; then
        echo "# found: $f"
        grep -E '^(SUPABASE_SERVICE_ROLE_KEY|ANON_KEY|JWT_SECRET|POSTGRES_PASSWORD|API_EXTERNAL_URL|SUPABASE_URL|SITE_URL|POSTGREST_URL)' "$f" 2>/dev/null || true
        echo
      fi
    done
fi

echo
echo "# If nothing printed above, look manually:"
echo "#   find / -maxdepth 6 -name '.env' 2>/dev/null | xargs grep -l 'SUPABASE_SERVICE_ROLE_KEY' 2>/dev/null"

