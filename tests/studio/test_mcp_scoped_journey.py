"""Scoped-token MCP journey over the S5/S7/S6 agent surface.

Real token minting (create_agent_token), real verify path, real scope gate;
only the Redis store and downstream services are faked. Proves:
- a read-scoped agent token sees and may call only read tools (write tools
  are absent from tools/list AND denied at tools/call);
- a plan-scoped agent token passes the scope gate on write tools and is
  then stopped before any paid call (config/asset gates, zero provider calls);
- an unknown or revoked token is 401.
No actual paid calls.
"""
from __future__ import annotations

import asyncio

import fakeredis
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services import agent_access, captions, source_assets, usage_ledger, usage_wallet, vision


def _run(coro):
    return asyncio.run(coro)


class _FakeRedis(fakeredis.FakeAsyncRedis):
    async def aclose(self):  # token store closes per call; the double survives
        return None


@pytest.fixture
def env(monkeypatch):
    fake = _FakeRedis(decode_responses=True)
    monkeypatch.setattr(usage_wallet, "_client", lambda: fake)
    for module in (captions, source_assets, usage_ledger, vision):
        monkeypatch.setattr(module.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("BLASTER_API_KEY", "test-operator-key")
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_VISION_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return fake


def _mint(scopes: list[str]) -> str:
    made = _run(agent_access.create_agent_token(name="journey", scopes=scopes,
                                                ttl_days=1, created_by="user:test"))
    assert made["ok"], made
    return made["token"]


def _call(client: TestClient, token: str, name: str, arguments: dict | None = None) -> dict:
    resp = client.post("/api/mcp",
                       headers={"Authorization": f"Bearer {token}"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": name, "arguments": arguments or {}}})
    assert resp.status_code == 200, resp.text
    return resp.json()["result"]["structuredContent"]


def _names(client: TestClient, token: str) -> set[str]:
    resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {token}"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp.status_code == 200, resp.text
    return {t["name"] for t in resp.json()["result"]["tools"]}


def test_read_scoped_token_sees_and_calls_only_read_tools(env):
    token = _mint(["read"])
    client = TestClient(app)
    names = _names(client, token)
    assert "get_captions" in names and "get_footage_analysis" in names
    assert "analyze_footage" not in names and "burn_captions" not in names
    assert "transcribe_footage" not in names
    denied = _call(client, token, "analyze_footage", {"asset_id": "asset-12345678"})
    assert denied["ok"] is False and denied["error"] == "scope_required"
    # read tool passes the gate and reaches the service layer
    read = _call(client, token, "get_footage_analysis", {"asset_id": "asset-12345678"})
    assert read["ok"] is False and read["error"] == "asset_not_found"


def test_plan_scoped_token_passes_scope_gate_then_config_gate(env):
    token = _mint(["plan"])
    client = TestClient(app)
    names = _names(client, token)
    assert "analyze_footage" in names and "transcribe_footage" in names
    # scope gate passed; the PAID call is stopped by a pre-flight gate
    res = _call(client, token, "analyze_footage", {"asset_id": "asset-12345678"})
    assert res["ok"] is False and res["error"] in ("asset_not_found", "model_not_configured")
    tr = _call(client, token, "transcribe_footage", {"asset_id": "asset-12345678"})
    assert tr["ok"] is False and tr["error"] == "asset_not_found"


def test_unknown_and_revoked_tokens_are_401(env):
    client = TestClient(app)
    resp = client.post("/api/mcp", headers={"Authorization": "Bearer bba_nope_nope"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp.status_code == 401
    token = _mint(["read"])
    token_id = token[len("bba_"):].split("_", 1)[0]
    _run(agent_access.revoke_agent_token(token_id, revoked_by="user:test"))
    resp = client.post("/api/mcp", headers={"Authorization": f"Bearer {token}"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp.status_code == 401
