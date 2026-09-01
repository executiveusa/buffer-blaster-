#!/usr/bin/env bash
set -Eeuo pipefail

# Buffer Blaster Phase 4 — sanitized schema/runtime probe.
# Read-only: this script does not mutate database, containers, files, or secrets.
# Gemini/server operator may override PG_CONTAINER and PG_DB when auto-discovery is ambiguous.

REPORT="${REPORT:-/tmp/buffer-blaster-phase4-server-report.md}"
PG_CONTAINER="${PG_CONTAINER:-}"
PG_DB="${PG_DB:-postgres}"

say() { printf '%s\n' "$*"; }

container_names() {
  docker ps --format '{{.Names}}' 2>/dev/null || true
}

if [[ -z "$PG_CONTAINER" ]]; then
  mapfile -t candidates < <(docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null | awk 'BEGIN{IGNORECASE=1} /postgres|supabase.*db/ {print $1}')
  if [[ ${#candidates[@]} -eq 1 ]]; then
    PG_CONTAINER="${candidates[0]}"
  elif [[ ${#candidates[@]} -gt 1 ]]; then
    say "Multiple PostgreSQL candidates found; set PG_CONTAINER explicitly and rerun:" >&2
    printf '  %s\n' "${candidates[@]}" >&2
    exit 3
  else
    say "No PostgreSQL container auto-detected. Set PG_CONTAINER explicitly." >&2
    exit 3
  fi
fi

psql_ro() {
  docker exec "$PG_CONTAINER" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$PG_DB" -AtF $'\t' -c "$1"
}

api_domain="unknown"
origin="unknown"
install_dir="unknown"
git_commit="unknown"

for dir in /opt/stavarai /opt/buffer-blaster /srv/buffer-blaster /app/buffer-blaster; do
  if [[ -d "$dir/.git" ]]; then
    install_dir="$dir"
    git_commit="$(git -C "$dir" rev-parse HEAD 2>/dev/null || echo unknown)"
    if [[ -f "$dir/.env.production" ]]; then
      api_domain="$(grep -E '^API_DOMAIN=' "$dir/.env.production" | tail -n1 | cut -d= -f2- || true)"
      origin="$(grep -E '^ALLOWED_ORIGINS=' "$dir/.env.production" | tail -n1 | cut -d= -f2- || true)"
      [[ -n "$api_domain" ]] || api_domain="unknown"
      [[ -n "$origin" ]] || origin="unknown"
    fi
    break
  fi
done

{
  echo "# Buffer Blaster Phase 4 Server Report"
  echo
  echo "## Identity"
  echo "- host: $(hostname 2>/dev/null || echo unknown)"
  echo "- os: $(. /etc/os-release 2>/dev/null && printf '%s %s' "${NAME:-unknown}" "${VERSION_ID:-unknown}" || echo unknown)"
  echo "- Buffer Blaster install: $install_dir"
  echo "- git commit: $git_commit"
  echo "- API domain: $api_domain"
  echo "- allowed origin: $origin"
  echo
  echo "## Relevant running containers"
  echo '```text'
  docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null | grep -Ei 'buffer|stavarai|supabase|postgres|postgrest|kong|gotrue|storage|caddy|coolify|redis' || true
  echo '```'
  echo
  echo "## Self-hosted Supabase"
  echo "- postgres container/service: $PG_CONTAINER"
  echo "- database: $PG_DB"
  echo
  echo "## Schema truth"
  echo
  echo "### Tables and RLS"
  echo '| table | rls |'
  echo '|---|---|'
  psql_ro "select c.relname, case when c.relrowsecurity then 'enabled' else 'disabled' end from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='buffer_blaster' and c.relkind='r' order by c.relname;" | while IFS=$'\t' read -r table rls; do
    printf '| %s | %s |\n' "$table" "$rls"
  done
  echo
  echo "### Columns"
  echo '| table | column | type | nullable | default |'
  echo '|---|---|---|---|---|'
  psql_ro "select table_name,column_name,data_type,is_nullable,coalesce(column_default,'') from information_schema.columns where table_schema='buffer_blaster' order by table_name,ordinal_position;" | while IFS=$'\t' read -r table col type nullable def; do
    def="${def//|/\\|}"
    printf '| %s | %s | %s | %s | %s |\n' "$table" "$col" "$type" "$nullable" "$def"
  done
  echo
  echo "### Foreign keys"
  echo '| constraint | source | source_type | target | target_type |'
  echo '|---|---|---|---|---|'
  psql_ro "select con.conname, ns.nspname||'.'||src.relname||'.'||sa.attname, format_type(sa.atttypid,sa.atttypmod), nt.nspname||'.'||tgt.relname||'.'||ta.attname, format_type(ta.atttypid,ta.atttypmod) from pg_constraint con join pg_class src on src.oid=con.conrelid join pg_namespace ns on ns.oid=src.relnamespace join pg_class tgt on tgt.oid=con.confrelid join pg_namespace nt on nt.oid=tgt.relnamespace join lateral unnest(con.conkey,con.confkey) with ordinality as k(srcatt,tgtatt,ord) on true join pg_attribute sa on sa.attrelid=src.oid and sa.attnum=k.srcatt join pg_attribute ta on ta.attrelid=tgt.oid and ta.attnum=k.tgtatt where con.contype='f' and ns.nspname='buffer_blaster' order by con.conname,k.ord;" | while IFS=$'\t' read -r con src stype tgt ttype; do
    printf '| %s | %s | %s | %s | %s |\n' "$con" "$src" "$stype" "$tgt" "$ttype"
  done
  echo
  echo "### RLS policies"
  echo '| table | policy | command | roles |'
  echo '|---|---|---|---|'
  psql_ro "select tablename,policyname,cmd,array_to_string(roles,',') from pg_policies where schemaname='buffer_blaster' order by tablename,policyname;" | while IFS=$'\t' read -r table policy cmd roles; do
    printf '| %s | %s | %s | %s |\n' "$table" "$policy" "$cmd" "$roles"
  done
  echo
  echo "### Critical money-loop contract"
  echo '```text'
  psql_ro "select table_name||'.'||column_name||' = '||data_type from information_schema.columns where table_schema='buffer_blaster' and table_name in ('campaigns','content_items','performance_events','experiments','experiment_variants','attribution_events','money_loop_receipts') order by table_name,ordinal_position;" || true
  echo '```'
  echo
  echo "## Configuration presence"
  echo '| variable | state |'
  echo '|---|---|'
  if [[ "$install_dir" != "unknown" && -f "$install_dir/.env.production" ]]; then
    vars=(API_DOMAIN ALLOWED_ORIGINS MASTER_ENCRYPTION_KEY BLASTER_API_KEY TRIAL_SESSION_SECRET REDIS_PASSWORD REDIS_URL BUFFER_BLASTER_WORKSPACE_ID SUPABASE_URL SUPABASE_SERVICE_KEY BUFFER_BLASTER_ASSET_BUCKET META_ACCESS_TOKEN META_AD_ACCOUNT_ID META_GRAPH_API_VERSION TIKTOK_ACCESS_TOKEN TIKTOK_ADVERTISER_ID TIKTOK_API_BASE_URL SHOPIFY_WEBHOOK_SECRET SHOPIFY_SHOP_DOMAIN SHOPIFY_ADMIN_ACCESS_TOKEN SHOPIFY_ADMIN_API_VERSION)
    for key in "${vars[@]}"; do
      val="$(grep -E "^${key}=" "$install_dir/.env.production" | tail -n1 | cut -d= -f2- || true)"
      if [[ -n "$val" ]]; then state=present; else state=missing; fi
      printf '| %s | %s |\n' "$key" "$state"
    done
    sb_url="$(grep -E '^SUPABASE_URL=' "$install_dir/.env.production" | tail -n1 | cut -d= -f2- || true)"
    if [[ "$sb_url" == *'.supabase.co'* ]]; then
      echo
      echo "**BLOCKER:** SUPABASE_URL points to managed Supabase, not the self-hosted stack."
    fi
  else
    echo '| .env.production | missing/not located |'
  fi
  echo
  echo "## Existing deployment health"
  echo '```text'
  docker ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null | grep -Ei 'buffer|stavarai|redis|caddy' || true
  echo '```'
  echo
  echo "## Final state"
  echo "READY_FOR_REPO_RECONCILIATION"
  echo
  echo "## Required next actions"
  echo "1. Compare this report to the Phase 4 branch contracts before any DDL."
  echo "2. If types/columns differ, fix repo + CI first and rerun tests."
  echo "3. Only then apply additive money-loop migrations and deploy the approved commit."
} > "$REPORT"

chmod 600 "$REPORT" || true
say "Sanitized report written to $REPORT"
