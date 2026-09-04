#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

MAX_CYCLES="${BUFFER_BLASTER_AUTOFINISH_MAX_CYCLES:-10}"
START_PHASE="${BUFFER_BLASTER_AUTOFINISH_START_PHASE:-1}"
REPORT="${BUFFER_BLASTER_AUTOFINISH_REPORT:-/tmp/buffer-blaster-autonomous-finish.md}"

PHASES=(
  "01|ugc-provider|docs/autonomous/phase-01-ugc-provider.md"
  "02|reference-ad|docs/autonomous/phase-02-reference-ad.md"
  "03|avatar-routing|docs/autonomous/phase-03-avatar-routing.md"
  "04|repurpose|docs/autonomous/phase-04-repurpose.md"
  "05|interoperability|docs/autonomous/phase-05-interoperability.md"
  "06|auth-budget-security|docs/autonomous/phase-06-auth-budget-security.md"
  "07|icm-docs|docs/autonomous/phase-07-icm-docs.md"
  "08|final-review|docs/autonomous/phase-08-final-review.md"
)

log(){ printf '[autofinish] %s\n' "$*"; }
die(){ printf '[autofinish] ERROR: %s\n' "$*" >&2; exit 1; }

for cmd in git python npm docker gh gemini npx; do command -v "$cmd" >/dev/null 2>&1 || die "$cmd is required"; done
if command -v ralphy >/dev/null 2>&1; then RALPHY=(ralphy); else RALPHY=(npx -y ralphy-cli); fi

install_skill(){
  local repo="$1"
  (cd "$HOME" && npx -y skills add "$repo" -y --all) >/tmp/buffer-blaster-skill-install.log 2>&1 || die "failed to install required skill $repo"
}

# Completion, simplification, prose, and independent-critic disciplines.
install_skill Leonxlnx/unlazy
install_skill DietrichGebert/ponytail
install_skill blader/humanizer
install_skill robonuggets/gauntlet-loop

cat >"$REPORT" <<EOF
# Buffer Blaster autonomous finish
- started_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- starting_main: $(git rev-parse origin/main 2>/dev/null || git rev-parse HEAD)
- state: RUNNING
EOF
chmod 600 "$REPORT"

run_repo_gates(){
  python -m pytest tests -q
  (
    cd frontend
    npm ci
    npm audit --audit-level=high
    npm run lint
    npm run build
  )
  docker compose -f docker-compose.prod.yml config >/tmp/buffer-blaster-compose-autofinish.yml
  bash scripts/selfhost/preflight.sh
}

run_post_merge_proof(){
  python -m pytest tests -q
  bash scripts/selfhost/smoke.sh
  python scripts/production/verify.py identity
}

verify_external_review_failure(){
  local name="$1" link="$2" run_id
  run_id="$(printf '%s' "$link" | sed -nE 's#.*actions/runs/([0-9]+).*#\1#p')"
  [[ -n "$run_id" ]] || die "$name failed but no review run id could be proven"
  if ! gh run view "$run_id" --log 2>/dev/null | grep -q 'github_models_retirement_brownout'; then
    die "$name failed for a reason other than the known GitHub Models retirement brownout"
  fi
  log "$name is externally blocked by the proven GitHub Models retirement brownout; not counted as a clean review"
}

wait_for_ci(){
  local pr="$1"
  set +e
  gh pr checks "$pr" --watch
  local watch_rc=$?
  set -e

  local checks
  checks="$(gh pr checks "$pr" --json name,bucket,state,link 2>/dev/null || echo '[]')"
  python - "$checks" <<'PY'
import json,sys
rows=json.loads(sys.argv[1])
allowed=('OpenCodeReview','Vibe Code Review')
material=[]
for r in rows:
    bucket=str(r.get('bucket','')).lower(); state=str(r.get('state','')).lower(); name=str(r.get('name',''))
    failed=bucket in {'fail','cancel'} or state in {'failure','cancelled','error'}
    if failed and not any(x.lower() in name.lower() for x in allowed):
        material.append((name,bucket or state))
if material:
    print('Material CI failures:', material, file=sys.stderr); raise SystemExit(1)
PY

  while IFS=$'\t' read -r name link; do
    [[ -z "$name" ]] && continue
    verify_external_review_failure "$name" "$link"
  done < <(printf '%s' "$checks" | python -c 'import json,sys,re; rows=json.load(sys.stdin); [print(f"{r.get(chr(110)+chr(97)+chr(109)+chr(101), chr(63))}\t{r.get(chr(108)+chr(105)+chr(110)+chr(107), chr(39)+chr(39))}") for r in rows if (str(r.get("bucket","")).lower() in {"fail","cancel"} or str(r.get("state","")).lower() in {"failure","cancelled","error"}) and re.search(r"OpenCodeReview|Vibe Code Review", str(r.get("name","")), re.I)]')

  if (( watch_rc != 0 )); then log "CI watch returned non-zero; all failed checks were either material-blocking or proven external brownouts"; fi
}

for entry in "${PHASES[@]}"; do
  IFS='|' read -r num slug prd <<<"$entry"
  (( 10#$num < START_PHASE )) && continue

  log "starting phase $num: $slug"
  git fetch origin
  git checkout main
  git reset --hard origin/main
  test -f "$prd" || die "missing phase PRD $prd on main"

  if ! grep -qE '^- \[ \]' "$prd"; then
    log "phase $num already complete in main; re-verifying"
    run_repo_gates
    continue
  fi

  branch="autofinish/phase-${num}-${slug}"
  git checkout -B "$branch" origin/main

  last=""; stalled=0
  for ((cycle=1; cycle<=MAX_CYCLES; cycle++)); do
    if ! grep -qE '^- \[ \]' "$prd"; then break; fi
    fingerprint="$(sha256sum "$prd" | awk '{print $1}')-$(git rev-parse HEAD)"
    if [[ "$fingerprint" == "$last" ]]; then stalled=$((stalled+1)); else stalled=0; fi
    last="$fingerprint"
    (( stalled >= 2 )) && die "phase $num made no observable progress for two cycles"

    log "phase $num Ralphy/Gemini cycle $cycle"
    set +e
    "${RALPHY[@]}" --gemini --prd "$prd" --base-branch main --max-retries 3
    rc=$?
    set -e
    printf '\n- phase_%s_cycle_%s_ralphy_exit: %s\n' "$num" "$cycle" "$rc" >>"$REPORT"
  done

  grep -qE '^- \[ \]' "$prd" && die "phase $num still has unchecked acceptance tasks"

  log "phase $num deterministic gates"
  run_repo_gates

  if git status --porcelain | grep -Eq '(^|/)(\.env($|\.)|.*\.pem$|.*\.key$|secrets/)'; then die "phase $num touched a secret-like path"; fi

  if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -m "Complete autonomous phase $num: $slug"
  fi
  git push -u origin "$branch" --force-with-lease

  pr="$(gh pr list --head "$branch" --base main --state open --json number --jq '.[0].number // empty')"
  if [[ -z "$pr" ]]; then
    url="$(gh pr create --base main --head "$branch" --title "Autofinish phase $num: $slug" --body "Autonomous phase governed by docs/AUTONOMOUS_FINISH_LOOP.md and $prd. Unlazy acceptance ledger + Ralphy/Gemini execution. Ponytail simplification and Humanizer apply where relevant. Merge only after deterministic gates and substantive CI. Human spend/publish/contract gates remain unchanged.")"
    pr="${url##*/}"
  fi

  wait_for_ci "$pr"
  head_sha="$(git rev-parse HEAD)"
  gh pr merge "$pr" --squash --delete-branch --match-head-commit "$head_sha"

  git fetch origin
  git checkout main
  git reset --hard origin/main
  log "phase $num merged; post-merge proof"
  run_post_merge_proof
  printf '\n- phase_%s: VERIFIED_AND_MERGED\n- main_after_phase_%s: %s\n' "$num" "$num" "$(git rev-parse HEAD)" >>"$REPORT"
done

for entry in "${PHASES[@]}"; do
  IFS='|' read -r _ _ prd <<<"$entry"
  grep -qE '^- \[ \]' "$prd" && die "unfinished acceptance task remains in $prd"
done

test -f ops/final-review/AUTONOMOUS_FINISH_REPORT.md || die "final review report is missing"
grep -q 'AUTONOMOUS_FINISH_VERIFIED' ops/final-review/AUTONOMOUS_FINISH_REPORT.md || die "final review report does not support verified state"

cat >>"$REPORT" <<EOF
- state: AUTONOMOUS_FINISH_VERIFIED
- completed_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- final_main: $(git rev-parse HEAD)
EOF
chmod 600 "$REPORT"
log "AUTONOMOUS_FINISH_VERIFIED — $REPORT"
