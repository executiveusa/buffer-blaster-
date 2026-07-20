#!/usr/bin/env bash
# ============================================================
#  deploy-frontend-vercel.sh — Vercel deploy of the Postatees frontend
#
#  Run from the repo root on the VPS (or a dev machine with the repo).
#  Creates a Vercel project if missing, sets env vars, deploys prod.
#
#  Architecture: frontend lives on Vercel (auto-HTTPS via *.vercel.app),
#  calls the FastAPI backend at $NEXT_PUBLIC_API_URL on the VPS.
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
hdr()  { echo -e "\n${BOLD}${BLUE}══ $1 ══${NC}"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FE_DIR="$REPO_DIR/frontend"

# ── 1. Vercel CLI ─────────────────────────────────────────────
hdr "1/4  VERCEL CLI"
if ! command -v vercel &>/dev/null; then
  info "installing Vercel CLI..."
  npm install -g vercel
fi
ok "vercel CLI: $(vercel --version 2>&1 | head -1)"

# ── 2. Token ──────────────────────────────────────────────────
hdr "2/4  VERCEL TOKEN"
TOKEN="${VERCEL_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  fail "VERCEL_TOKEN env var not set. Get one at https://vercel.com/account/tokens then:
    export VERCEL_TOKEN=vcp_xxx
    bash scripts/deploy-frontend-vercel.sh"
fi
ok "VERCEL_TOKEN is set"

# ── 3. Project (link or create) ───────────────────────────────
hdr "3/4  PROJECT LINK"
cd "$FE_DIR"

# Create .vercel/ locally if missing — `vercel link` does this interactively,
# but we use the API to create the project non-interactively.
PROJECT_NAME="postatees-stavarai"
info "ensuring Vercel project '$PROJECT_NAME' exists..."

# Try to link; if it fails, create the project via API.
if ! vercel link --yes --token "$TOKEN" 2>/dev/null; then
  info "creating new Vercel project '$PROJECT_NAME'..."
  vercel project add "$PROJECT_NAME" --token "$TOKEN" || warn "project may already exist"
  vercel link --yes --token "$TOKEN" 2>/dev/null || true
fi
ok "linked to Vercel project"

# ── 4. Env vars + deploy ──────────────────────────────────────
hdr "4/4  ENV + DEPLOY"

VPS_IP="${VPS_IP:-31.220.58.212}"
API_PORT="${API_PORT:-8002}"
API_URL="http://$VPS_IP:$API_PORT"

info "setting Vercel env vars..."

# env add is idempotent-safe if we ignore errors on duplicates
echo "true" | vercel env add NEXT_PUBLIC_DEMO_MODE production --token "$TOKEN" 2>/dev/null || true
echo "$API_URL" | vercel env add NEXT_PUBLIC_API_URL production --token "$TOKEN" 2>/dev/null || true
echo "BLASTER2026" | vercel env add DEMO_PASSWORD production --token "$TOKEN" 2>/dev/null || true

ok "env vars set"

info "deploying to production..."
DEPLOY_OUTPUT=$(vercel deploy --prod --yes --token "$TOKEN" 2>&1 | tee /dev/stderr)
DEPLOY_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[a-z0-9-]+\.vercel\.app' | tail -1)

if [ -z "$DEPLOY_URL" ]; then
  fail "couldn't parse deploy URL from output above. Check Vercel dashboard."
fi

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  POSTATEES FRONTEND DEPLOYED                  ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Landing:${NC}  $DEPLOY_URL"
echo -e "  ${BOLD}Blog:${NC}     $DEPLOY_URL/blog"
echo -e "  ${BOLD}Admin:${NC}    $DEPLOY_URL/admin  (password: BLASTER2026)"
echo -e "  ${BOLD}API:${NC}      $API_URL/api/health"
echo ""
echo -e "  ${YELLOW}Mixed-content warning:${NC} frontend is HTTPS, API is HTTP."
echo -e "  Browsers may block API calls until the API is on HTTPS too."
echo -e "  Options: (a) buy a domain + Caddy TLS, (b) Cloudflare Tunnel."
echo -e "  See docs/POSTATEES_DEPLOY.md §6."
echo ""
