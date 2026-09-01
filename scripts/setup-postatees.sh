#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility entrypoint only. This legacy installer carried obsolete
# Postatees/Stavarai paths, a known password, direct-IP HTTP wiring, and a
# separate systemd deployment model. Buffer Blaster now has one canonical
# self-hosted deployment path.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "NOTICE: scripts/setup-postatees.sh is deprecated." >&2
echo "Routing to scripts/selfhost/install.sh." >&2
exec "$ROOT/scripts/selfhost/install.sh" "$@"
