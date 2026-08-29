"""Minimal MCP JSON-RPC surface over the same studio services.

This is intentionally separate from TryPost's own MCP server: agents can use
this server for the proprietary campaign/UGC layer, while publishing is routed
through the replaceable TryPost REST adapter.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..services.integration_auth import verify_operator
from ..services.media_generation import get_media_provider
from ..services.publishing import PublishRequest, get_publisher
from ..services.social_drop import SocialDrop, platform_payload
from ..services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from ..services.video_prompt import VideoPromptInput, compile_video_prompt
from .studio import CampaignBrief, _campaign_plan

router = APIRouter(tags=["mcp"])

MCP_TOOLS: list[dict[str, Any]] = [
    {"name": "studio_status", "description": "Return media, publishing, approval and interface status.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "create_campaign_plan", "description": "Create a bounded social campaign plan from a brand objective.", "inputSchema": {"type": "object", "required": ["brand", "objective"], "properties": {"brand": {"type": "string"}, "objective": {"type": "string"}, "audience": {"type": "string"}, "offer": {"type": "string"}, "duration_days": {"type": "integer", "minimum": 1, "maximum": 30}, "platforms": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "create_ugc_prompt", "description": "Compile a production UGC video prompt from a structured brief.", "inputSchema": {"type": "object", "required": ["idea"], "properties": {"idea": {"type": "string"}, "product": {"type": "string"}, "camera": {"type": "string"}, "subject": {"type": "string"}, "environment": {"type": "string"}, "lighting": {"type": "string"}, "style": {"type": "string"}, "motion": {"type": "string"}, "dialogue": {"type": ["string", "null"]}, "platform": {"type": "string"}, "aspect_ratio": {"type": "string"}}}},
    {"name": "create_ugc_ad_factory_plan", "description": "Turn a product truth brief into a gated two-clip UGC ad production plan with ICM stages, continuity rules and quote metadata.", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism"], "properties": {"product": {"type": "string"}, "audience": {"type": "string"}, "pain": {"type": "string"}, "mechanism": {"type": "string"}, "offer": {"type": "string"}, "platform": {"type": "string"}, "actor_description": {"type": "string"}, "delivery_tone": {"type": "string"}, "visual_lane": {"type": "string"}}}},
    {"name": "list_social_accounts", "description": "List connected social accounts from the optional publishing integration.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "schedule_social_drop", "description": "Schedule an explicitly approved Social Drop through the publishing kernel.", "inputSchema": {"type": "object", "required": ["id", "content", "format", "platforms", "scheduled_at", "approved"], "properties": {"id": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "object"}}, "scheduled_at": {"type": "string"}, "approved": {"type": "boolean"}, "media_urls": {"type": "array", "items": {"type": "string"}}}}},
]


def _ok(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    import json
    return {"content": [{"type": "text", "text": json.dumps(value)}], "structuredContent": value, **({"isError": True} if is_error else {})}


@router.post("/api/mcp")
async def mcp(request: Request) -> JSONResponse:
    try:
        verify_operator(request)
    except Exception as exc:
        status = getattr(exc, "status_code", 401)
        return JSONResponse({"error": "unauthorized"}, status_code=status)

    message = await request.json()
    request_id = message.get("id")
    method = message.get("method")
    if message.get("jsonrpc") != "2.0":
        return JSONResponse(_error(request_id, -32600, "Invalid Request"), status_code=400)
    if method == "initialize":
        return JSONResponse(_ok(request_id, {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "social-studio", "version": "1.0.0"}}))
    if method == "notifications/initialized":
        return JSONResponse({}, status_code=204)
    if method == "ping":
        return JSONResponse(_ok(request_id, {}))
    if method == "tools/list":
        return JSONResponse(_ok(request_id, {"tools": MCP_TOOLS}))
    if method != "tools/call":
        return JSONResponse(_error(request_id, -32601, "Method not found"), status_code=404)

    name = message.get("params", {}).get("name")
    args = message.get("params", {}).get("arguments") or {}
    try:
        if name == "studio_status":
            value = {"media": get_media_provider().status(), "publishing": get_publisher().status(), "approval_gate": True}
        elif name == "create_campaign_plan":
            value = _campaign_plan(CampaignBrief(**args))
        elif name == "create_ugc_prompt":
            value = {"prompt": compile_video_prompt(VideoPromptInput(**args))}
        elif name == "create_ugc_ad_factory_plan":
            value = build_ugc_factory_plan(UGCFactoryBrief(**args))
        elif name == "list_social_accounts":
            value = await get_publisher().list_accounts()
        elif name == "schedule_social_drop":
            drop = SocialDrop(**args)
            errors = drop.validate()
            if errors:
                value = {"ok": False, "error": "invalid_social_drop", "details": errors}
            else:
                value = await get_publisher().schedule(PublishRequest(
                    content=drop.content,
                    platforms=platform_payload(drop),
                    scheduled_at=drop.scheduled_at or "",
                    approved=drop.approved,
                    media_urls=drop.media_urls,
                ))
        else:
            return JSONResponse(_error(request_id, -32602, "Unknown tool"))
        return JSONResponse(_ok(request_id, _tool_result(value, is_error=isinstance(value, dict) and value.get("ok") is False)))
    except Exception as exc:
        return JSONResponse(_error(request_id, -32603, f"Tool failed: {type(exc).__name__}"))
