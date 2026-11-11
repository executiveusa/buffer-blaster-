"""Agent-facing artifacts must match the real app, so they cannot drift."""
from __future__ import annotations

import json
from pathlib import Path

from api.app import app
from api.routers.mcp import MCP_TOOLS, TOOL_SCOPES, tool_scope
from api.services.agent_access import SCOPES
from scripts.agent.build_chatgpt_action import AGENT_OPERATIONS, build

ROOT = Path(__file__).resolve().parents[1]


def test_chatgpt_action_matches_live_openapi_and_excludes_privileged_routes():
    spec = build("https://example.invalid")
    live = app.openapi()["paths"]
    for (method, path) in AGENT_OPERATIONS:
        assert method in live[path], (method, path)
    exported = {p for p in spec["paths"]}
    for forbidden in ("/api/agent/tokens", "/api/studio/billing/internal-wallet", "/api/studio/billing/activate"):
        assert forbidden not in exported
    assert not any(p.startswith("/api/studio/money-loop") or p.startswith("/api/admin") for p in exported)
    assert not any("decision" in p for p in exported)
    committed = json.loads((ROOT / "plugins/chatgpt/openapi.agent.json").read_text())
    assert set(committed["paths"]) == exported, "regenerate plugins/chatgpt/openapi.agent.json"


def test_claude_plugin_points_at_the_mcp_endpoint_with_an_env_token():
    manifest = json.loads((ROOT / "plugins/claude/.claude-plugin/plugin.json").read_text())
    mcp = json.loads((ROOT / "plugins/claude/.mcp.json").read_text())["mcpServers"]["buffer-blaster"]
    assert manifest["name"] == "buffer-blaster"
    assert mcp["url"].endswith("/api/mcp")
    assert mcp["headers"]["Authorization"] == "Bearer ${BLASTER_AGENT_TOKEN}"
    skill = (ROOT / "plugins/claude/skills/buffer-blaster/SKILL.md").read_text()
    assert "approval_id" in skill and "request_render_approval" in skill


def test_every_mcp_tool_has_a_valid_scope_and_is_documented():
    doc = (ROOT / "docs/AGENT_ACCESS.md").read_text() + (ROOT / "plugins/social-studio/SKILL.md").read_text()
    names = [t["name"] for t in MCP_TOOLS]
    assert len(names) == len(set(names))
    for name in names:
        assert tool_scope(name) in SCOPES
    assert set(TOOL_SCOPES) <= set(names)
    for new_tool in ("whoami", "estimate_ugc_ad_factory", "request_render_approval", "request_publish_approval", "get_approval"):
        assert new_tool in doc


def test_llms_txt_present_and_does_not_advertise_disabled_openapi():
    text = (ROOT / "frontend/public/llms.txt").read_text()
    assert text.startswith("# Buffer Blaster\n")
    assert "/api/backend/api/mcp" in text
    assert "/openapi.json)" not in text
