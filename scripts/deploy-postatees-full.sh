#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility entrypoint only. The former one-shot deploy searched unrelated
# filesystem locations for a Supabase service-role key, injected a known
# password, used direct-IP HTTP URLs, and applied an obsolete namespaced
# migration path. Those behaviors violate Buffer Blaster's current security and
# canonical-schema contracts.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "NOTICE: scripts/deploy-postatees-full.sh is deprecated." >&2
echo "Routing to scripts/selfhost/install.sh." >&2
exec "$ROOT/scripts/selfhost/install.sh" "$@"
