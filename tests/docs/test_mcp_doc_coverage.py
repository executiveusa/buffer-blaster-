"""Every MCP tool must have a docs entry (Global DoD #6)."""
from __future__ import annotations

import pathlib

from api.routers.mcp import MCP_TOOLS

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").rglob("*.md"))


def test_every_mcp_tool_is_documented():
    corpus = ""
    for rel in DOCS:
        path = ROOT / rel
        if path.exists():
            corpus += path.read_text()
    missing = [t["name"] for t in MCP_TOOLS if t["name"] not in corpus]
    assert not missing, f"MCP tools lacking a doc entry in {DOCS}: {missing}"
