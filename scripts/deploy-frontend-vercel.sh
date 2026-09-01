#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility entrypoint only. The former implementation could deploy demo
# mode to production, inject a known password, and point an HTTPS frontend at a
# plain-HTTP VPS address. Keep one production path instead.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "NOTICE: scripts/deploy-frontend-vercel.sh is deprecated." >&2
echo "Routing to the canonical Buffer Blaster Vercel configurator." >&2
exec "$ROOT/scripts/selfhost/configure-vercel.sh" "$@"
