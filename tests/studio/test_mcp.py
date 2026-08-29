from fastapi.testclient import TestClient

from api.app import app
from api.routers.mcp import MCP_TOOLS


def _tool(name: str) -> dict:
    return next(tool for tool in MCP_TOOLS if tool["name"] == name)


def test_mcp_exposes_agent_first_surface():
    names = {tool["name"] for tool in MCP_TOOLS}
    assert {
        "studio_status",
        "create_campaign_plan",
        "create_ugc_prompt",
        "create_ugc_ad_factory_plan",
        "render_ugc_ad_factory_clip",
        "list_social_accounts",
        "schedule_social_drop",
    }.issubset(names)


def test_mcp_preserves_existing_ugc_motion_schema():
    motion = _tool("create_ugc_prompt")["inputSchema"]["properties"]["motion"]
    assert motion == {"type": "string"}


def test_factory_render_tool_requires_explicit_approval_field():
    schema = _tool("render_ugc_ad_factory_clip")["inputSchema"]
    assert "approved" in schema["required"]
    assert schema["properties"]["approved"] == {"type": "boolean"}


def test_authenticated_agent_can_call_ugc_factory(monkeypatch):
    monkeypatch.setenv("BLASTER_API_KEY", "test-agent-key")
    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        headers={"x-api-key": "test-agent-key"},
        json={
            "jsonrpc": "2.0",
            "id": "ugc-factory-proof",
            "method": "tools/call",
            "params": {
                "name": "create_ugc_ad_factory_plan",
                "arguments": {
                    "product": "Cella Coffee",
                    "audience": "home baristas",
                    "pain": "my coffee keeps tasting flat even when the beans are good",
                    "mechanism": "the brew variables stay simple and repeatable",
                    "offer": "POUR15",
                    "platform": "instagram"
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = payload["result"]["structuredContent"]
    assert plan["ok"] is True
    assert plan["factory_version"] == "ugc-ad-factory-v1"
    assert len(plan["clips"]) == 2
    assert plan["commercial"]["billable_unit"] == "finished_ugc_ad"
    assert plan["commercial"]["charges_customer"] is False
    assert plan["approval_required_before_publish"] is True


def test_agent_factory_render_refuses_unapproved_spend(monkeypatch):
    monkeypatch.setenv("BLASTER_API_KEY", "test-agent-key")
    client = TestClient(app)
    response = client.post(
        "/api/mcp",
        headers={"x-api-key": "test-agent-key"},
        json={
            "jsonrpc": "2.0",
            "id": "ugc-render-no-approval",
            "method": "tools/call",
            "params": {
                "name": "render_ugc_ad_factory_clip",
                "arguments": {
                    "product": "Cella Coffee",
                    "audience": "home baristas",
                    "pain": "my coffee keeps tasting flat even when the beans are good",
                    "mechanism": "the brew variables stay simple and repeatable",
                    "offer": "POUR15",
                    "platform": "instagram",
                    "clip_number": 1,
                    "approved": False
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    result = payload["result"]["structuredContent"]
    assert result["ok"] is False
    assert result["error"] == "human_approval_required"
    assert result["approval_required"] is True
