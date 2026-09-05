"""Buffer Blaster MCP JSON-RPC surface over the canonical Studio services.

Agents can plan freely. Paid generation requires an active server-owned wallet
and explicit approval, exactly like the REST/UI path. Publishing remains an
optional downstream integration behind explicit approval.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..services.asset_storage import get_asset_storage
from ..services.integration_auth import verify_operator
from ..services.media_contracts import UGCPlanDraft
from ..services.media_generation import get_media_provider
from ..services.media_ops import get_media_ops
from ..services.media_receipts import create_ugc_plan, get_ugc_plan
from ..services.performance_ingestion import sync_experiment
from ..services.pricing import public_pricing
from ..services.provider_registry import ProviderRouteRequest, plan_provider_route, provider_registry
from ..services.publishing import PublishRequest, get_publisher
from ..services.reference_ad import ReferenceAdIntake, analyze_reference_ad, get_reference_strategy
from ..services.repurpose import RepurposePlanRequest, create_repurpose_plan, get_repurpose_plan
from ..services.shopify_context import ShopifyProductContextRequest, create_shopify_context, get_shopify_context
from ..services.social_drop import SocialDrop, platform_payload
from ..services.studio_ledger import create_campaign, get_job, list_jobs, summary
from ..services.ugc_executor import execute_ugc_factory_ad
from ..services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from ..services.usage_wallet import get_wallet, reserve_generation
from ..services.video_prompt import VideoPromptInput, compile_video_prompt
from .studio import CampaignBrief, _campaign_plan

router = APIRouter(tags=["mcp"])

_FACTORY_PROPERTIES = {
    "product": {"type": "string"},
    "audience": {"type": "string"},
    "pain": {"type": "string"},
    "mechanism": {"type": "string"},
    "offer": {"type": "string"},
    "platform": {"type": "string"},
    "actor_description": {"type": "string"},
    "delivery_tone": {"type": "string"},
    "visual_lane": {"type": "string"},
}

_UGC_PLAN_SCHEMA = UGCPlanDraft.model_json_schema()
_REFERENCE_SCHEMA = ReferenceAdIntake.model_json_schema()
_PROVIDER_ROUTE_SCHEMA = ProviderRouteRequest.model_json_schema()
_REPURPOSE_SCHEMA = RepurposePlanRequest.model_json_schema()
_SHOPIFY_CONTEXT_SCHEMA = ShopifyProductContextRequest.model_json_schema()

MCP_TOOLS: list[dict[str, Any]] = [
    {"name": "studio_status", "description": "Return canonical media, storage, ledger, pricing, publishing and approval status.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_pricing", "description": "Return configured package economics and the standard generation cost ceiling.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_creative_jobs", "description": "List canonical creative-job receipts from the Studio ledger.", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}}}},
    {"name": "get_creative_job", "description": "Get one canonical creative-job receipt by id.", "inputSchema": {"type": "object", "required": ["job_id"], "properties": {"job_id": {"type": "string"}}}},
    {"name": "get_usage_wallet", "description": "Get the remaining generation allowance, provider-cost budget, state and expiration for a server-owned wallet.", "inputSchema": {"type": "object", "required": ["wallet_id"], "properties": {"wallet_id": {"type": "string"}}}},
    {"name": "create_campaign_plan", "description": "Create and persist a bounded social campaign plan from a brand objective.", "inputSchema": {"type": "object", "required": ["brand", "objective"], "properties": {"brand": {"type": "string"}, "objective": {"type": "string"}, "audience": {"type": "string"}, "offer": {"type": "string"}, "duration_days": {"type": "integer", "minimum": 1, "maximum": 30}, "platforms": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "create_ugc_prompt", "description": "Compile a no-spend UGC video prompt from a structured brief.", "inputSchema": {"type": "object", "required": ["idea"], "properties": {"idea": {"type": "string"}, "product": {"type": "string"}, "camera": {"type": "string"}, "subject": {"type": "string"}, "environment": {"type": "string"}, "lighting": {"type": "string"}, "style": {"type": "string"}, "motion": {"type": "string"}, "dialogue": {"type": ["string", "null"]}, "platform": {"type": "string"}, "aspect_ratio": {"type": "string"}}}},
    {"name": "create_ugc_plan", "description": "Create and persist a provider-neutral, no-spend UGC plan receipt with workspace-scoped idempotency.", "inputSchema": _UGC_PLAN_SCHEMA},
    {"name": "get_ugc_plan", "description": "Read one canonical UGC plan receipt inside the configured workspace.", "inputSchema": {"type": "object", "required": ["plan_id"], "properties": {"plan_id": {"type": "string", "format": "uuid"}}}},
    {"name": "analyze_reference_ad", "description": "Analyze a rights-authorized reference ad into mechanics and persist control plus two original no-spend UGC plans.", "inputSchema": _REFERENCE_SCHEMA},
    {"name": "get_reference_strategy", "description": "Read one reference strategy receipt and its linked variant plans inside the configured workspace.", "inputSchema": {"type": "object", "required": ["receipt_id"], "properties": {"receipt_id": {"type": "string", "format": "uuid"}}}},
    {"name": "list_provider_capabilities", "description": "List server-owned UGC/avatar provider capabilities without exposing secrets or model identifiers.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "plan_provider_route", "description": "Choose a governed provider capability and estimated cost without reserving spend. Client input may only lower server-owned ceilings.", "inputSchema": _PROVIDER_ROUTE_SCHEMA},
    {"name": "create_repurpose_plan", "description": "Turn transcript-backed long-form source media into deterministic ranked short-form clip plans without provider spend.", "inputSchema": _REPURPOSE_SCHEMA},
    {"name": "get_repurpose_plan", "description": "Read one canonical repurpose-plan receipt from the creative-job ledger.", "inputSchema": {"type": "object", "required": ["plan_id"], "properties": {"plan_id": {"type": "string"}}}},
    {"name": "create_shopify_product_context", "description": "Persist minimal Shopify product truth as a no-spend workspace-scoped creative context receipt.", "inputSchema": _SHOPIFY_CONTEXT_SCHEMA},
    {"name": "get_shopify_product_context", "description": "Read one Shopify product-context receipt inside the configured workspace.", "inputSchema": {"type": "object", "required": ["receipt_id"], "properties": {"receipt_id": {"type": "string"}}}},
    {"name": "sync_experiment_evidence", "description": "Read provider metrics plus Shopify attribution for one workspace-scoped experiment and return the deterministic evaluation receipt. Does not launch or activate ads.", "inputSchema": {"type": "object", "required": ["experiment_id"], "properties": {"experiment_id": {"type": "string"}}}},
    {"name": "create_ugc_ad_factory_plan", "description": "Turn product truth into a gated two-clip UGC production plan with cost estimate and continuity rules. This does not spend.", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism"], "properties": _FACTORY_PROPERTIES}},
    {"name": "execute_ugc_ad_factory", "description": "Execute a full two-clip UGC ad to a durable final asset. Requires explicit approval and an active paid wallet; provider spend is reserved server-side before generation.", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism", "wallet_id", "approved"], "properties": {**_FACTORY_PROPERTIES, "wallet_id": {"type": "string"}, "approved": {"type": "boolean"}}}},
    {"name": "list_social_accounts", "description": "List social accounts from the optional downstream publishing integration.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "schedule_social_drop", "description": "Schedule an explicitly approved Social Drop through the optional publishing boundary.", "inputSchema": {"type": "object", "required": ["id", "content", "format", "platforms", "scheduled_at", "approved"], "properties": {"id": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "object"}}, "scheduled_at": {"type": "string"}, "approved": {"type": "boolean"}, "media_urls": {"type": "array", "items": {"type": "string"}}}}},
]


def _ok(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    import json
    return {"content": [{"type": "text", "text": json.dumps(value)}], "structuredContent": value, **({"isError": True} if is_error else {})}


async def _execute_factory(args: dict[str, Any]) -> dict[str, Any]:
    render_args = dict(args)
    wallet_id = str(render_args.pop("wallet_id", ""))
    approved = bool(render_args.pop("approved", False))
    if not approved:
        return {"ok": False, "error": "human_approval_required", "approval_required": True, "state": "planned"}
    wallet = await get_wallet(wallet_id)
    if not wallet:
        return {"ok": False, "error": "wallet_not_found"}
    if wallet.get("state") != "active":
        return {"ok": False, "error": "wallet_not_active", "wallet_state": wallet.get("state")}

    brief = UGCFactoryBrief(**render_args)
    plan = build_ugc_factory_plan(brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}
    estimated_cost = int(plan.get("commercial", {}).get("estimated_generation_cost_cents") or 0)
    if not get_media_provider().configured:
        return {"ok": False, "error": "media_provider_not_configured", "state": "preflight_blocked"}
    if not get_asset_storage().configured:
        return {"ok": False, "error": "asset_storage_not_configured", "state": "preflight_blocked"}
    if not get_media_ops().available():
        return {"ok": False, "error": "ffmpeg_not_available", "state": "preflight_blocked"}

    reservation = await reserve_generation(wallet_id, estimated_provider_cost_cents=estimated_cost)
    if not reservation.get("ok"):
        return {**reservation, "state": "spend_blocked"}
    reservation["offer_id"] = wallet["offer_id"]
    return await execute_ugc_factory_ad(brief, approved=True, offer_id=str(wallet["offer_id"]), reserved_allowance=reservation)


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
        return JSONResponse(_ok(request_id, {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "buffer-blaster", "version": "2.0.0"}}))
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
            value = {"ok": True, "media": get_media_provider().status(), "storage": get_asset_storage().status(), "media_ops": {"ffmpeg": get_media_ops().available()}, "publishing": get_publisher().status(), "ledger": await summary(), "pricing": public_pricing(), "approval_gate": True}
        elif name == "get_pricing":
            value = public_pricing()
        elif name == "list_creative_jobs":
            rows = await list_jobs(int(args.get("limit", 50)))
            value = {"ok": True, "jobs": rows, "count": len(rows)}
        elif name == "get_creative_job":
            row = await get_job(str(args.get("job_id", "")))
            value = {"ok": bool(row), "job": row, "error": None if row else "job_not_found"}
        elif name == "get_usage_wallet":
            row = await get_wallet(str(args.get("wallet_id", "")))
            value = {"ok": bool(row), "wallet": row, "error": None if row else "wallet_not_found"}
        elif name == "create_campaign_plan":
            plan = _campaign_plan(CampaignBrief(**args))
            persisted = await create_campaign(plan)
            value = {"ok": not bool(persisted.get("ledger_error")), "plan": plan, "ledger": persisted}
        elif name == "create_ugc_prompt":
            value = {"ok": True, "prompt": compile_video_prompt(VideoPromptInput(**args)), "paid_generation": False}
        elif name == "create_ugc_plan":
            value = await create_ugc_plan(UGCPlanDraft(**args))
        elif name == "get_ugc_plan":
            value = await get_ugc_plan(str(args.get("plan_id", "")))
        elif name == "analyze_reference_ad":
            value = await analyze_reference_ad(ReferenceAdIntake(**args))
        elif name == "get_reference_strategy":
            value = await get_reference_strategy(str(args.get("receipt_id", "")))
        elif name == "list_provider_capabilities":
            value = {"ok": True, "providers": [entry.model_dump(mode="json") for entry in provider_registry()], "paid_generation": False}
        elif name == "plan_provider_route":
            value = await plan_provider_route(ProviderRouteRequest(**args))
        elif name == "create_repurpose_plan":
            value = await create_repurpose_plan(RepurposePlanRequest(**args))
        elif name == "get_repurpose_plan":
            value = await get_repurpose_plan(str(args.get("plan_id", "")))
        elif name == "create_shopify_product_context":
            value = await create_shopify_context(ShopifyProductContextRequest(**args))
        elif name == "get_shopify_product_context":
            value = await get_shopify_context(str(args.get("receipt_id", "")))
        elif name == "sync_experiment_evidence":
            value = await sync_experiment(str(args.get("experiment_id", "")))
        elif name == "create_ugc_ad_factory_plan":
            value = build_ugc_factory_plan(UGCFactoryBrief(**args))
        elif name == "execute_ugc_ad_factory":
            value = await _execute_factory(args)
        elif name == "list_social_accounts":
            value = await get_publisher().list_accounts()
        elif name == "schedule_social_drop":
            drop = SocialDrop(**args)
            errors = drop.validate()
            if errors:
                value = {"ok": False, "error": "invalid_social_drop", "details": errors}
            else:
                value = await get_publisher().schedule(PublishRequest(content=drop.content, platforms=platform_payload(drop), scheduled_at=drop.scheduled_at or "", approved=drop.approved, media_urls=drop.media_urls))
        else:
            return JSONResponse(_error(request_id, -32602, "Unknown tool"))
        return JSONResponse(_ok(request_id, _tool_result(value, is_error=isinstance(value, dict) and value.get("ok") is False)))
    except Exception as exc:
        return JSONResponse(_error(request_id, -32603, f"Tool failed: {type(exc).__name__}"))
