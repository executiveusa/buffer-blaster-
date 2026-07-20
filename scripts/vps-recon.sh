#!/usr/bin/env bash
# ============================================================
#  vps-recon.sh — READ-ONLY Postatees VPS inspection.
#  Run ON the VPS, as the user Postatees will deploy under.
#  Changes nothing. Prints everything I need to write the deploy script.
#
#  From your Windows PowerShell:
#     ssh root@31.220.58.212            (or whatever user/host your hostinger box uses)
#     # once on the box:
#     curl -fsSL https://raw.githubusercontent.com/executiveusa/buffer-blaster-/main/scripts/vps-recon.sh | bash
#  ...or scp this file up and run:  bash vps-recon.sh
#
#  Then copy the full output back into the chat.
# ============================================================
set +e

echo "===== 1. OS / KERNEL / ARCH ====="
if [ -f /etc/os-release ]; then . /etc/os-release; echo "OS: $PRETTY_NAME"; fi
uname -a
echo "arch: $(uname -m)"

echo ""
echo "===== 2. RESOURCES ====="
echo "CPU cores: $(nproc)"
free -h | head -2
df -h / | head -2

echo ""
echo "===== 3. INSTALLED RUNTIMES (what we'll need) ====="
for c in node npm python3 pip3 cargo rustc git nginx caddy docker docker-compose pm2 systemctl supabase rtk jcodemunch-mcp; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" --version 2>&1 | head -1)
    printf "  ✓ %-18s %s\n" "$c" "$v"
  else
    printf "  ✗ %-18s not installed\n" "$c"
  fi
done

echo ""
echo "===== 4. WHAT'S LISTENING (ports 80, 443, 3000, 5432, 5434, 8000, 8080) ====="
ss -tlnp 2>/dev/null | grep -E ':(80|443|3000|5432|5434|8000|8080)\b' || echo "  (nothing on those ports, or ss lacks permission — try sudo)"

echo ""
echo "===== 5. WEB SERVERS / REVERSE PROXIES ====="
systemctl list-units --type=service --state=running 2>/dev/null | grep -iE 'nginx|caddy|apache|httpd|traefik' || echo "  none running"

echo ""
echo "===== 6. EXISTING BRAND DIRECTORIES (best guess) ====="
ls -1 /home 2>/dev/null
echo "---"
ls -1 /var/www 2>/dev/null || echo "  no /var/www"
echo "---"
ls -1 /opt 2>/dev/null

echo ""
echo "===== 7. POSTATEES-SPECIFIC ====="
id postatees 2>/dev/null || echo "  no 'postatees' user yet"
ls -la /home/postatees 2>/dev/null || echo "  no /home/postatees yet"
find / -maxdepth 4 -iname "*postatees*" 2>/dev/null | head -10

echo ""
echo "===== 8. PROCESS MANAGERS ====="
systemctl is-active pm2-stavarai 2>/dev/null && echo "  pm2 unit exists"
pm2 list 2>/dev/null | head -10 || echo "  pm2 not running"

echo ""
echo "===== 9. WHO AM I / SUDO ====="
whoami
id
sudo -n true 2>/dev/null && echo "  passwordless sudo: yes" || echo "  passwordless sudo: no (will prompt)"

echo ""
echo "===== 10. OUTBOUND NETWORK (can the box reach GitHub/Supabase/Vercel?) ====="
curl -sI -m 5 https://github.com 2>&1 | head -1
curl -sI -m 5 https://api.supabase.co 2>&1 | head -1
curl -sI -m 5 https://vercel.com 2>&1 | head -1

echo ""
echo "===== RECON COMPLETE — copy everything above back to the chat ====="
