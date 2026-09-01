#!/usr/bin/env bash
# ============================================================
# install-tools.sh — RTK + jcodemunch global agent install
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
hdr()  { echo -e "\n${BLUE}══ $1 ══${NC}"; }

hdr "INSTALLING RTK (Rust Token Killer)"
if command -v rtk &>/dev/null; then
  ok "rtk already installed: $(rtk --version 2>&1 | head -1)"
else
  info "Installing rtk via cargo..."
  if ! command -v cargo &>/dev/null; then
    fail "cargo not found. Install rustup first: https://rustup.rs"
  fi
  cargo install rtk-cli
  ok "rtk installed"
fi

info "Smoke-testing rtk..."
if rtk --version &>/dev/null; then
  ok "rtk ready. Prefix agent commands: \`rtk cargo test\`, \`rtk npm run build\`"
else
  warn "rtk installed but not on PATH. Restart your shell or add ~/.cargo/bin to PATH."
fi

hdr "INSTALLING JCODEMUNCH-MCP"
if python3 -c "import jcodemunch_mcp" 2>/dev/null || command -v jcodemunch-mcp &>/dev/null; then
  ok "jcodemunch-mcp already installed"
else
  info "Installing jcodemunch-mcp via pip..."
  if command -v uv &>/dev/null; then
    uv tool install jcodemunch-mcp
  else
    pip3 install --user jcodemunch-mcp
  fi
  ok "jcodemunch-mcp installed"
fi

MCP_CONFIG_DIR="${HOME}/.config/mcp"
mkdir -p "$MCP_CONFIG_DIR"

info "Registering jcodemunch MCP server..."
cat > "$MCP_CONFIG_DIR/jcodemunch.json" << 'JSON'
{
  "mcpServers": {
    "jcodemunch": {
      "command": "jcodemunch-mcp",
      "args": [],
      "env": {}
    }
  }
}
JSON
ok "MCP config written to $MCP_CONFIG_DIR/jcodemunch.json"

hdr "REGISTERING GLOBAL SKILLS"
SKILL_DIRS=(
  "${HOME}/.hermes/skills"
  "${HOME}/.claude/skills"
)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for dir in "${SKILL_DIRS[@]}"; do
  mkdir -p "$dir"
  if [ -d "${REPO_ROOT}/skills" ]; then
    cp -r "${REPO_ROOT}/skills/"* "$dir/" 2>/dev/null && \
      ok "Copied repo skills → $dir" || warn "no skills/ to copy"
  fi
done

for dir in "${SKILL_DIRS[@]}"; do
  mkdir -p "$dir/grinions-buffer-blaster"
  cat > "$dir/grinions-buffer-blaster/SKILL.md" << 'SKILL'
---
name: grinions-buffer-blaster
description: GRINIONS v1 operating contract for Buffer Blaster. Read EMERALD_TABLETS.md and AGENTS.md before any code change.
---

# GRINIONS Buffer Blaster

When operating in the Buffer Blaster repo (`buffer-blaster-`):

1. Read `EMERALD_TABLETS.md` and `AGENTS.md` first.
2. Verify It Before Everything (V.I.B.E.) — no completion claim without evidence.
3. Use `jcodemunch index` once per session for symbol retrieval when available.
4. Prefix CLI commands with `rtk` when installed.
5. One phase = one accepted OpenSpec change = one PR. Squash-merge only.
6. One `.beads/{timestamp}_{action}.bead` per destructive operation.
7. Never log operator passwords, API keys, service-role keys, or provider secrets.
8. Publishing and paid-media spend remain human approval-gated.
9. Stop conditions are in `EMERALD_TABLETS.md §6`.
SKILL
done
ok "GRINIONS Buffer Blaster skill pointer written to global skill dirs"

hdr "VERIFY"
echo ""
echo -e "  ${GREEN}rtk:${NC}          $(command -v rtk || echo 'NOT ON PATH — restart shell')"
echo -e "  ${GREEN}jcodemunch:${NC}   $(command -v jcodemunch-mcp || python3 -c 'import jcodemunch_mcp; print("python module ok")' 2>/dev/null || echo 'NOT INSTALLED')"
echo -e "  ${GREEN}skills:${NC}       ${HOME}/.hermes/skills + ${HOME}/.claude/skills"
echo ""
echo -e "  ${YELLOW}Next:${NC}"
echo -e "   1. Restart your shell so \`rtk\` is on PATH."
echo -e "   2. In the agent host, import $MCP_CONFIG_DIR/jcodemunch.json"
echo -e "   3. In the repo: \`jcodemunch index\` to build the symbol index."
echo -e "   4. Prefix agent commands: \`rtk cargo test\`, \`rtk npm run build\`."
