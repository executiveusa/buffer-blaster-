#!/usr/bin/env bash
# Quick diagnostic: what's on :8002, and what does our clients table look like?
set -uo pipefail

echo "===== A. WHAT'S ON PORT 8002? ====="
ss -tlnp 2>/dev/null | grep ':8002' || echo "  nothing on 8002"
echo
echo "  Process detail:"
ss -tlnp 2>/dev/null | grep ':8002' | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 | xargs -I{} -- ps -p {} -o pid,user,cmd --no-headers 2>/dev/null || echo "  (couldn't resolve pid)"

echo
echo "===== B. IS OUR SERVICE ACTUALLY RUNNING? ====="
systemctl status postatees-stavarai-api --no-pager 2>&1 | head -10

echo
echo "===== C. OUR SERVICE LOG (last 30 lines) ====="
tail -30 /var/log/postatees-stavarai-api.log 2>/dev/null || echo "  no log file"

echo
echo "===== D. WHAT DOES public.clients LOOK LIKE IN THE SUPABASE DB? ====="
docker exec -i supabase-db psql -U postgres -d postgres -c '\d public.clients' 2>&1 | head -30

echo
echo "===== E. WHAT OTHER 'clients'-like TABLES EXIST? ====="
docker exec -i supabase-db psql -U postgres -d postgres -c "
  SELECT table_schema, table_name
  FROM information_schema.tables
  WHERE table_name LIKE '%client%' OR table_name = 'beads' OR table_name = 'content_units'
  ORDER BY table_schema, table_name;
" 2>&1

echo
echo "===== F. WHAT SCHEMAS EXIST IN THE DB? ====="
docker exec -i supabase-db psql -U postgres -d postgres -c "
  SELECT schema_name FROM information_schema.schemata
  WHERE schema_name NOT LIKE 'pg_%' AND schema_name NOT IN ('information_schema')
  ORDER BY schema_name;
" 2>&1

echo
echo "===== G. WHAT PORTS ARE FREE IN THE 8002-8050 RANGE? ====="
for p in 8002 8003 8004 8005 8010 8020 8030 8040 8050; do
  if ss -tlnH 2>/dev/null | grep -q ":$p "; then
    echo "  :$p  TAKEN"
  else
    echo "  :$p  free"
  fi
done
