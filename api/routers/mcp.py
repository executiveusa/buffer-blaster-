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
from ..services.agent_access import gate_publish, get_approval, is_agent, list_approvals, publish_payload, request_approval
from ..services import captions, footage, footage_import, usage_ledger, vision
from ..services.consistency import compile_shot_prompt, create_identity, get_identity, list_identities, shot_preflight
from ..services.recipes import list_recipes
from ..services.factory_runner import estimate_factory, request_render_approval, run_factory
from ..services.integration_auth import request_scopes, verify_operator
from ..services.supabase_auth import EXECUTE_ROLES
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
from ..services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from ..services.usage_wallet import get_wallet
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
    "casting_reference_url": {"type": "string", "description": "Optional https URL of the approved character reference still. Fed to clip 1 as the image input so the first shot is anchored to the cast creator."},
    "casting_reference_urls": {"type": "array", "items": {"type": "string"}, "maxItems": 12, "description": "Optional https URLs of approved identity reference assets (multi-angle/expression stills). Applied to BOTH clips through the provider's env-declared reference-images list field; the clip-2 continuity seed stays a separate start-frame input. Fails closed when the provider capability is not configured."},
    "clip_audio_urls": {"type": "array", "items": {"type": "string"}, "maxItems": 2, "description": "Optional https audio URLs, one fixed slot per clip (blank slot = no pinned audio for that clip, slots never shift), pinned to the generated soundtrack on the provider's env-declared, route-allowlisted audio-URL field (replaces the generated soundtrack per vendor docs; NOT a lip-sync or voice input). Distinct from the boolean generate_audio flag; fails closed when the capability is not configured for the selected route."},
}

_UGC_PLAN_SCHEMA = UGCPlanDraft.model_json_schema()
_REFERENCE_SCHEMA = ReferenceAdIntake.model_json_schema()
_PROVIDER_ROUTE_SCHEMA = ProviderRouteRequest.model_json_schema()
_REPURPOSE_SCHEMA = RepurposePlanRequest.model_json_schema()
_SHOPIFY_CONTEXT_SCHEMA = ShopifyProductContextRequest.model_json_schema()

MCP_TOOLS: list[dict[str, Any]] = [
    {"name": "studio_status", "description": "Return canonical media, storage, ledger, pricing, publishing and approval status.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_usage_summary", "description": "Read the append-only spend ledger: totals grouped by day, model, job or agent. Estimated and actual cents are reported separately and never mixed.", "inputSchema": {"type": "object", "properties": {"group_by": {"type": "string", "enum": ["day", "model", "job", "agent"]}}}},
    {"name": "connect_source", "description": "Get a footage-source consent URL (Google Drive / OneDrive) or the Dropbox Chooser app key. Returns the consent URL only; a human completes OAuth, and tokens are stored encrypted server-side, never exposed to agents.", "inputSchema": {"type": "object", "required": ["provider"], "properties": {"provider": {"type": "string", "enum": ["google", "onedrive", "dropbox"]}}}},
    {"name": "list_footage", "description": "List connection status and, for a connected provider, remote video files. Never returns token material.", "inputSchema": {"type": "object", "properties": {"provider": {"type": "string", "enum": ["google", "onedrive", "dropbox"]}}}},
    {"name": "import_footage", "description": "Import one picked footage file into the asset store: SSRF allowlist, 2 GB cap, MIME sniff and sha256 provenance. Zero-cost transfer; writes no usage rows.", "inputSchema": {"type": "object", "required": ["provider", "filename", "idempotency_key"], "properties": {"provider": {"type": "string", "enum": ["google", "onedrive", "dropbox"]}, "filename": {"type": "string"}, "idempotency_key": {"type": "string"}, "file_id": {"type": "string"}, "link": {"type": "string"}}}},
    {"name": "transcribe_footage", "description": "Transcribe one stored asset with self-hosted faster-whisper: word timestamps, grouped cues (max 2 lines, <=42 chars/line, 9:16 safe), SRT + VTT. Cached forever by content sha256; zero-cost, recorded at actual_cents=0.", "inputSchema": {"type": "object", "required": ["asset_id"], "properties": {"asset_id": {"type": "string"}}}},
    {"name": "burn_captions", "description": "Burn cached captions into a video with the brand style (Inter, ink/lime, 9:16 bottom-safe). Writes a NEW captioned asset; the original is never modified.", "inputSchema": {"type": "object", "required": ["asset_id"], "properties": {"asset_id": {"type": "string"}}}},
    {"name": "analyze_footage", "description": "Run bounded agent vision on one stored asset (1 frame/2s, max 24 frames at 512px): scenes, hook candidates, product visibility, quality flags, suggested cuts. PAID provider call: requires configured vendor pricing, runs under S4 caps, cached by content sha256, linkable to a plan.", "inputSchema": {"type": "object", "required": ["asset_id"], "properties": {"asset_id": {"type": "string"}, "plan_id": {"type": "string"}}}},
    {"name": "get_footage_analysis", "description": "Read the cached vision analysis for an asset. No recompute; returns not_analyzed until analyze_footage has run.", "inputSchema": {"type": "object", "required": ["asset_id"], "properties": {"asset_id": {"type": "string"}}}},
    {"name": "get_captions", "description": "Read the cached transcript/cues/SRT/VTT for an asset. No recompute; returns not_transcribed until transcribe_footage has run.", "inputSchema": {"type": "object", "required": ["asset_id"], "properties": {"asset_id": {"type": "string"}}}},
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
    {"name": "execute_ugc_ad_factory", "description": "Execute a full two-clip UGC ad to a durable final asset. Requires approval, an active wallet, and an idempotency key so retries cannot reserve spend twice.", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism", "wallet_id", "idempotency_key"], "properties": {**_FACTORY_PROPERTIES, "wallet_id": {"type": "string"}, "idempotency_key": {"type": "string", "minLength": 8, "maxLength": 128}, "approved": {"type": "boolean", "description": "Human operators only. Agent tokens must pass approval_id instead."}, "approval_id": {"type": "string", "description": "A human-approved render approval from request_render_approval."}}}},
    {"name": "list_social_accounts", "description": "List social accounts from the optional downstream publishing integration.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "schedule_social_drop", "description": "Schedule an explicitly approved Social Drop through the optional publishing boundary.", "inputSchema": {"type": "object", "required": ["id", "content", "format", "platforms", "scheduled_at", "approved"], "properties": {"id": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "object"}}, "scheduled_at": {"type": "string"}, "approved": {"type": "boolean"}, "approval_id": {"type": "string"}, "media_urls": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "whoami", "description": "Show this caller's identity, scopes, and whether it can grant approvals. Agents start here.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "estimate_ugc_ad_factory", "description": "Price a two-clip UGC ad with the exact server pricing used at execution. No spend, no reservation.", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism"], "properties": _FACTORY_PROPERTIES}},
    {"name": "request_render_approval", "description": "Ask a human to approve one render of this exact brief from this wallet. The server sets the cost ceiling. Returns approval_id (pending).", "inputSchema": {"type": "object", "required": ["product", "audience", "pain", "mechanism", "wallet_id"], "properties": {**_FACTORY_PROPERTIES, "wallet_id": {"type": "string"}}}},
    {"name": "request_publish_approval", "description": "Ask a human to approve publishing this exact Social Drop. Returns approval_id (pending).", "inputSchema": {"type": "object", "required": ["content", "platforms", "scheduled_at"], "properties": {"content": {"type": "string"}, "format": {"type": "string"}, "platforms": {"type": "array", "items": {"type": "object"}}, "scheduled_at": {"type": "string"}, "media_urls": {"type": "array", "items": {"type": "string"}}, "campaign_id": {"type": "string"}}}},
    {"name": "get_approval", "description": "Read one approval and its status (pending, approved, rejected, consumed).", "inputSchema": {"type": "object", "required": ["approval_id"], "properties": {"approval_id": {"type": "string"}}}},
    {"name": "list_approvals", "description": "List approvals in this workspace, optionally by status.", "inputSchema": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "approved", "rejected", "consumed"]}}}},
    {"name": "create_identity", "description": "Save a character, product or location as a named set of reference photos (no training). Optional character sheet URL and identity block. No spend.", "inputSchema": {"type": "object", "required": ["kind", "name", "photos"], "properties": {"kind": {"type": "string", "enum": ["character", "product", "location"]}, "name": {"type": "string"}, "photos": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 12}, "sheet_url": {"type": "string"}, "identity_block": {"type": "string"}}}},
    {"name": "list_identities", "description": "List saved characters, products and locations with consistency readiness.", "inputSchema": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["character", "product", "location"]}}}},
    {"name": "compile_shot_prompt", "description": "Build a shot prompt from an Identity Block (static look only) and a Motion Block (camera/action only). Rejects mixed blocks and ages in video prompts, which cause identity drift.", "inputSchema": {"type": "object", "required": ["identity_block", "motion_block"], "properties": {"identity_block": {"type": "string"}, "motion_block": {"type": "string"}, "references": {"type": "integer", "minimum": 0, "maximum": 9}}}},
    {"name": "preflight_shot", "description": "List every reason a paid video call would be wasted (no approved hero frame, scene over 15 s, unsupported duration/ratio, model without image input, prompt split violations, take limit) before any spend.", "inputSchema": {"type": "object", "required": ["shot"], "properties": {"shot": {"type": "object"}, "identity_id": {"type": "string"}, "provider_caps": {"type": "object"}}}},
    {"name": "list_recipes", "description": "List UGC ad recipes (testimonial, unboxing, product hero, problem/solution, before/after, try-on). Each shot is a motion block of 15 s or less; pair with a saved character/product identity block.", "inputSchema": {"type": "object", "properties": {}}},
]

# Scope each tool needs when called with an agent token. Unlisted tools need "plan".
TOOL_SCOPES: dict[str, str] = {
    **{name: "read" for name in (
        "studio_status", "get_pricing", "list_creative_jobs", "get_creative_job", "get_usage_wallet", "get_ugc_plan",
        "get_reference_strategy", "get_repurpose_plan", "get_shopify_product_context", "list_provider_capabilities",
        "list_social_accounts", "get_approval", "list_approvals", "whoami", "list_identities", "list_recipes",
        "get_usage_summary", "list_footage", "get_captions", "get_footage_analysis",
    )},
    "execute_ugc_ad_factory": "render",
    "request_render_approval": "render",
    "schedule_social_drop": "publish",
    "request_publish_approval": "publish",
}


def tool_scope(name: str) -> str:
    return TOOL_SCOPES.get(name, "plan")


# Tools that persist records or can invoke a provider (mirrors the gated REST
# routes). Human callers need an execute role; agent tokens keep their scope
# checks above. Read and pure-compute tools stay open to every member.
MCP_WRITE_TOOLS = {
    "create_campaign_plan", "create_ugc_plan", "analyze_reference_ad", "create_repurpose_plan",
    "create_shopify_product_context", "sync_experiment_evidence", "schedule_social_drop",
    "create_identity", "request_render_approval", "request_publish_approval",
    "compile_shot_prompt", "preflight_shot", "execute_ugc_ad_factory",
    "connect_source", "import_footage", "transcribe_footage", "burn_captions", "analyze_footage",
}


def _ok(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    import json
    return {"content": [{"type": "text", "text": json.dumps(value)}], "structuredContent": value, **({"isError": True} if is_error else {})}


async def _execute_factory(args: dict[str, Any], identity: str, role: str | None = None) -> dict[str, Any]:
    render_args = dict(args)
    return await run_factory(
        render_args,
        wallet_id=str(render_args.get("wallet_id", "")),
        idempotency_key=str(render_args.get("idempotency_key", "")),
        approved=bool(render_args.get("approved", False)),
        identity=identity,
        approval_id=(str(render_args["approval_id"]) if render_args.get("approval_id") else None),
        role=role,
    )


@router.post("/api/mcp")
async def mcp(request: Request) -> JSONResponse:
    try:
        identity = await verify_operator(request)
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
        scopes = request_scopes(request)
        return JSONResponse(_ok(request_id, {"tools": [t for t in MCP_TOOLS if tool_scope(t["name"]) in scopes]}))
    if method != "tools/call":
        return JSONResponse(_error(request_id, -32601, "Method not found"), status_code=404)

    name = message.get("params", {}).get("name")
    args = message.get("params", {}).get("arguments") or {}
    if name and tool_scope(str(name)) not in request_scopes(request):
        denied = {"ok": False, "error": "scope_required", "scope": tool_scope(str(name))}
        return JSONResponse(_ok(request_id, _tool_result(denied, is_error=True)))
    if name and str(name) in MCP_WRITE_TOOLS and not is_agent(identity):
        role = getattr(request.state, "role", None)
        if role not in EXECUTE_ROLES:
            denied = {"ok": False, "error": "role_denied", "detail": f"Role '{role or 'none'}' cannot call {name}."}
            return JSONResponse(_ok(request_id, _tool_result(denied, is_error=True)))
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
        elif name == "get_usage_summary":
            value = await usage_ledger.usage_report(group_by=str(args.get("group_by") or "day"))
        elif name == "connect_source":
            value = await footage.consent_url(str(args.get("provider", "")), actor=identity)
        elif name == "list_footage":
            provider = args.get("provider")
            if provider:
                value = await footage.list_files(str(provider))
            else:
                value = await footage.connection_status()
        elif name == "import_footage":
            value = await footage_import.import_footage(
                provider=str(args.get("provider", "")), actor=identity,
                filename=str(args.get("filename", "")), idempotency_key=str(args.get("idempotency_key", "")),
                file_id=args.get("file_id"), link=args.get("link"))
        elif name == "transcribe_footage":
            value = await captions.transcribe_by_asset_id(asset_id=str(args.get("asset_id", "")), actor=identity)
        elif name == "burn_captions":
            value = await captions.burn_by_asset_id(asset_id=str(args.get("asset_id", "")), actor=identity)
        elif name == "get_captions":
            value = await captions.get_captions(asset_id=str(args.get("asset_id", "")))
        elif name == "analyze_footage":
            value = await vision.analyze_footage(asset_id=str(args.get("asset_id", "")),
                                                 plan_id=args.get("plan_id") or None, actor=identity)
        elif name == "get_footage_analysis":
            value = await vision.get_footage_analysis(asset_id=str(args.get("asset_id", "")))
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
            value = await _execute_factory(args, identity, role=getattr(request.state, "role", None))
        elif name == "list_social_accounts":
            value = await get_publisher().list_accounts()
        elif name == "schedule_social_drop":
            drop_args = {k: v for k, v in args.items() if k != "approval_id"}
            gate = await gate_publish(identity=identity, fields=drop_args, approved=bool(args.get("approved")), approval_id=args.get("approval_id"),
                                      role=getattr(request.state, "role", None))
            drop = SocialDrop(**{**drop_args, "approved": bool(gate.get("ok"))})
            errors = drop.validate()
            if not gate.get("ok"):
                value = {"ok": False, **{k: v for k, v in gate.items() if k != "ok"}}
            elif errors:
                value = {"ok": False, "error": "invalid_social_drop", "details": errors}
            else:
                value = await get_publisher().schedule(PublishRequest(content=drop.content, platforms=platform_payload(drop), scheduled_at=drop.scheduled_at or "", approved=drop.approved, media_urls=drop.media_urls))
        elif name == "list_recipes":
            value = list_recipes()
        elif name == "create_identity":
            value = await create_identity(kind=str(args.get("kind", "")), name=str(args.get("name", "")), photos=list(args.get("photos") or []),
                                          sheet_url=args.get("sheet_url"), identity_block=str(args.get("identity_block") or ""), created_by=identity)
        elif name == "list_identities":
            value = await list_identities(args.get("kind"))
        elif name == "compile_shot_prompt":
            value = compile_shot_prompt(str(args.get("identity_block", "")), str(args.get("motion_block", "")), references=int(args.get("references") or 0))
        elif name == "preflight_shot":
            ident = None
            if args.get("identity_id"):
                found = await get_identity(str(args["identity_id"]))
                ident = found.get("identity") if found.get("ok") else {"photos": []}
            value = shot_preflight(dict(args.get("shot") or {}), identity=ident, provider_caps=args.get("provider_caps"))
        elif name == "whoami":
            value = {"ok": True, "identity": identity, "agent": is_agent(identity), "scopes": sorted(request_scopes(request)), "can_grant_approvals": not is_agent(identity)}
        elif name == "estimate_ugc_ad_factory":
            value = {k: v for k, v in estimate_factory(args).items() if k != "plan"}
        elif name == "request_render_approval":
            value = await request_render_approval(args, wallet_id=str(args.get("wallet_id", "")), requested_by=identity)
        elif name == "request_publish_approval":
            value = await request_approval(kind="publish", payload=publish_payload(args), requested_by=identity, summary=f"Publish to {len(args.get('platforms') or [])} platform(s)")
        elif name == "get_approval":
            value = await get_approval(str(args.get("approval_id", "")))
        elif name == "list_approvals":
            value = await list_approvals(args.get("status"))
        else:
            return JSONResponse(_error(request_id, -32602, "Unknown tool"))
        return JSONResponse(_ok(request_id, _tool_result(value, is_error=isinstance(value, dict) and value.get("ok") is False)))
    except Exception as exc:
        return JSONResponse(_error(request_id, -32603, f"Tool failed: {type(exc).__name__}"))