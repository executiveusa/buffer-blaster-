#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BRANCH="${BUFFER_BLASTER_FINISH_BRANCH:-phase/05-live-provider-verification}"
PRD="docs/PRODUCTION_FINISH_PRD.md"
MAX_CYCLES="${BUFFER_BLASTER_FINISH_MAX_CYCLES:-12}"
REPORT="${BUFFER_BLASTER_FINISH_REPORT:-/tmp/buffer-blaster-production-finisher.md}"
DEPLOY_AFTER_MERGE="${BUFFER_BLASTER_DEPLOY_AFTER_MERGE:-1}"

log() { printf '[production-finisher] %s\n' "$*"; }
die() { printf '[production-finisher] ERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v python >/dev/null || die "python is required"
command -v npm >/dev/null || die "npm is required"
command -v docker >/dev/null || die "docker is required"
command -v gemini >/dev/null || die "Gemini CLI is required on this production-finisher host"

if command -v ralphy >/dev/null 2>&1; then
  RALPHY=(ralphy)
else
  command -v npx >/dev/null || die "ralphy or npx is required"
  RALPHY=(npx -y ralphy-cli)
fi

log "syncing $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  die "tracked working tree is dirty before finisher start"
fi

cat >"$REPORT" <<EOF
# Buffer Blaster production finisher

- branch: $BRANCH
- started_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- initial_sha: $(git rev-parse HEAD)
- state: RUNNING
EOF

last_fingerprint=""
stalled=0
for ((cycle=1; cycle<=MAX_CYCLES; cycle++)); do
  if ! grep -qE '^- \[ \]' "$PRD"; then
    log "PRD has no pending tasks"
    break
  fi

  fingerprint="$(sha256sum "$PRD" | awk '{print $1}')-$(git rev-parse HEAD)"
  if [[ "$fingerprint" == "$last_fingerprint" ]]; then
    stalled=$((stalled+1))
  else
    stalled=0
  fi
  last_fingerprint="$fingerprint"
  if (( stalled >= 2 )); then
    printf '\n- state: BLOCKED_NO_PROGRESS\n- cycle: %s\n' "$cycle" >>"$REPORT"
    die "two consecutive cycles made no observable PRD/commit progress; inspect provider or external blockers in $REPORT"
  fi

  log "Ralphy/Gemini cycle $cycle"
  set +e
  "${RALPHY[@]}" --gemini --prd "$PRD" --base-branch "$BRANCH" --max-retries 3
  ralphy_status=$?
  set -e
  printf '\n- cycle_%s_ralphy_exit: %s\n' "$cycle" "$ralphy_status" >>"$REPORT"
  git status --short >>"$REPORT" || true
  git rev-parse HEAD >>"$REPORT"
done

if grep -qE '^- \[ \]' "$PRD"; then
  pending="$(grep -cE '^- \[ \]' "$PRD" || true)"
  printf '\n- state: BLOCKED_PENDING_TASKS\n- pending_tasks: %s\n' "$pending" >>"$REPORT"
  die "$pending production tasks remain after $MAX_CYCLES cycles"
fi

log "running deterministic release gates"
python -m pytest tests -q
(
  cd frontend
  npm ci
  npm run lint
  npm run build
)
docker compose -f docker-compose.prod.yml config >/tmp/buffer-blaster-compose.yml
grep -q selfhost_supabase /tmp/buffer-blaster-compose.yml
bash scripts/selfhost/preflight.sh
bash scripts/selfhost/smoke.sh
python scripts/production/verify.py health
python scripts/production/verify.py provider-report /tmp/buffer-blaster-phase5-provider-report.md
python -m pytest tests/studio/test_money_loop_providers.py tests/selfhost -q
python scripts/production/verify.py runtime
python scripts/production/verify.py identity
python scripts/production/verify.py prd "$PRD"
python scripts/production/verify.py gauntlet ops/final-gauntlet/adpanel-receipt.json

if git status --porcelain | grep -Eq '(^|/)(\.env|.*\.pem$|.*\.key$|secrets/)'; then
  die "refusing to commit a secret-like path"
fi
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "Finish Buffer Blaster production release"
fi

git push origin "$BRANCH"

if command -v gh >/dev/null 2>&1; then
  pr_number="$(gh pr list --head "$BRANCH" --base main --state open --json number --jq '.[0].number // empty')"
  if [[ -z "$pr_number" ]]; then
    pr_url="$(gh pr create --base main --head "$BRANCH" --title 'Finish Buffer Blaster production release' --body 'Autonomous production-finisher output. Completion is evidence-gated by GATES.production.md; real ad spend remains behind the explicit human approval and budget-ceiling gate.')"
    pr_number="$(printf '%s' "$pr_url" | sed -E 's#.*/pull/([0-9]+).*#\1#')"
  fi
  log "waiting for PR #$pr_number checks"
  gh pr checks "$pr_number" --watch --fail-fast
  gh pr merge "$pr_number" --squash --delete-branch
else
  die "all local gates passed but gh CLI is unavailable; cannot safely complete PR/CI/merge stage"
fi

if [[ "$DEPLOY_AFTER_MERGE" == "1" ]]; then
  log "deploying verified merged main"
  git fetch origin
  git checkout main
  git reset --hard origin/main
  COMPOSE=(docker compose -f docker-compose.prod.yml)
  if [[ -n "${BUFFER_BLASTER_COMPOSE_OVERRIDE:-}" ]]; then
    COMPOSE+=(-f "$BUFFER_BLASTER_COMPOSE_OVERRIDE")
  fi
  "${COMPOSE[@]}" up -d --build --remove-orphans
  bash scripts/selfhost/preflight.sh
  bash scripts/selfhost/smoke.sh
  python scripts/production/verify.py health
  python scripts/production/verify.py runtime
fi

cat >>"$REPORT" <<EOF

- state: PRODUCTION_VERIFIED
- completed_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- deployed_sha: $(git rev-parse HEAD)
EOF
chmod 600 "$REPORT"
log "PRODUCTION_VERIFIED — report: $REPORT"
