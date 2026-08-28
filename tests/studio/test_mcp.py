from api.routers.mcp import MCP_TOOLS


def test_mcp_exposes_agent_first_surface():
    names = {tool["name"] for tool in MCP_TOOLS}
    assert {
        "studio_status",
        "create_campaign_plan",
        "create_ugc_prompt",
        "list_social_accounts",
        "schedule_social_drop",
    }.issubset(names)
