"""Agent-first operational API for campaigns, UGC, billing, and approvals."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.asset_storage import get_asset_storage
from ..services.billing import activate_checkout_session
from ..services.integration_auth import verify_operator
from ..services.media_generation import get_media_provider
from ..services.media_ops import get_media_ops
from ..services.pricing import public_pricing
from ..services.publishing import PublishRequest, get_publisher
from ..services.social_drop import SocialDrop, platform_payload
from ..services.studio_ledger import create_campaign, get_job, list_jobs, summary
from ..services.ugc_executor import execute_ugc_factory_ad
from ..services.ugc_factory import UGCFactoryBrief as ServiceUGCFactoryBrief, build_ugc_factory_plan
from ..services.video_prompt import VideoPromptInput, compile_video_prompt
from ..services.voice_intent import parse_voice_intent
from ..services.usage_wallet import get_wallet, reserve_generation

router = APIRouter(prefix="/api/studio", tags=["studio"])


class CampaignBrief(BaseModel):
    brand: str
    objective: str
    audience: str = "customers and prospects"
    offer: str = ""
    duration_days: int = Field(default=7, ge=1, le=30)
    platforms: list[str] = Field(default_factory=lambda: ["instagram", "facebook"])


class UGCBrief(BaseModel):
    idea: str
    product: str = ""
    camera: str = "stable handheld medium shot with one smooth push-in"
    subject: str = "a natural creator demonstrating the product"
    environment: str = "a believable everyday setting"
    lighting: str = "soft natural light"
    style: str = "realistic"
    motion: str = "small continuous movements with natural pacing"
    dialogue: str | None = None
    platform: str = "instagram"
    aspect_ratio: str = "9:16"


class UGCFactoryPlanRequest(BaseModel):
    product: str
    audience: str
    pain: str
    mechanism: str
    offer: str = ""
    platform: str = "instagram"
    actor_description: str = "a natural creator speaking like they are sharing something they actually use"
    delivery_tone: str = "calm, honest and direct"
    visual_lane: str = "lane_zero"


class UGCFactoryExecuteRequest(UGCFactoryPlanRequest):
    wallet_id: str
    approved: bool = False


class BillingActivationRequest(BaseModel):
    checkout_session_id: str


class ScheduleRequest(BaseModel):
    id: str
    content: str
    format: str = "post"
    platforms: list[dict[str, Any]]
    scheduled_at: str
    approved: bool = False
    media_urls: list[str] = Field(default_factory=list)
    campaign_id: str | None = None


class AgentCommand(BaseModel):
    command: str


def _campaign_plan(brief: CampaignBrief) -> dict[str, Any]:
    formats = ["reel", "post", "carousel", "post", "reel", "post", "carousel"]
    angles = ["problem and tension", "product proof", "use case", "objection handling", "UGC testimonial", "offer and urgency", "community proof"]
    days = []
    for index in range(brief.duration_days):
        days.append({
            "day": index + 1,
            "format": formats[index % len(formats)],
            "angle": angles[index % len(angles)],
            "platforms": brief.platforms,
            "cta": brief.offer or brief.objective,
            "state": "draft",
        })
    return {
        "id": f"campaign-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "brand": brief.brand,
        "objective": brief.objective,
        "audience": brief.audience,
        "offer": brief.offer,
        "days": days,
        "approval_required_before_publish": True,
    }


@router.get("/status")
async def status(_=Depends(verify_operator)) -> dict[str, Any]:
    return {
        "ok": True,
        "media": get_media_provider().status(),
        "storage": get_asset_storage().status(),
        "media_ops": {"ffmpeg": get_media_ops().available()},
        "publishing": get_publisher().status(),
        "ledger": await summary(),
        "pricing": public_pricing(),
        "approval_gate": True,
        "interfaces": ["ui", "rest", "mcp", "cli", "plugin", "voice"],
    }


@router.get("/pricing")
async def pricing(_=Depends(verify_operator)) -> dict[str, Any]:
    return public_pricing()


@router.get("/ledger/summary")
async def ledger_summary(_=Depends(verify_operator)) -> dict[str, Any]:
    return await summary()


@router.get("/jobs")
async def jobs(limit: int = 50, _=Depends(verify_operator)) -> dict[str, Any]:
    rows = await list_jobs(limit)
    return {"ok": True, "jobs": rows, "count": len(rows)}


@router.get("/jobs/{job_id}")
async def job(job_id: str, _=Depends(verify_operator)) -> dict[str, Any]:
    row = await get_job(job_id)
    return {"ok": bool(row), "job": row, "error": None if row else "job_not_found"}


@router.post("/billing/activate")
async def activate_billing(request: BillingActivationRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    return await activate_checkout_session(request.checkout_session_id)


@router.get("/billing/wallet/{wallet_id}")
async def wallet(wallet_id: str, _=Depends(verify_operator)) -> dict[str, Any]:
    row = await get_wallet(wallet_id)
    return {"ok": bool(row), "wallet": row, "error": None if row else "wallet_not_found"}


@router.post("/campaigns/plan")
async def plan_campaign(brief: CampaignBrief, _=Depends(verify_operator)) -> dict[str, Any]:
    plan = _campaign_plan(brief)
    persisted = await create_campaign(plan)
    return {"ok": not bool(persisted.get("ledger_error")), "plan": plan, "ledger": persisted}


@router.post("/ugc/prompt")
async def create_ugc_prompt(brief: UGCBrief, _=Depends(verify_operator)) -> dict[str, Any]:
    prompt = compile_video_prompt(VideoPromptInput(**brief.model_dump()))
    return {"ok": True, "prompt": prompt, "brief": brief.model_dump(), "paid_generation": False}


@router.post("/ugc/factory/plan")
async def create_ugc_factory_plan(brief: UGCFactoryPlanRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    return build_ugc_factory_plan(ServiceUGCFactoryBrief(**brief.model_dump()))


@router.post("/ugc/factory/execute")
async def execute_factory(request: UGCFactoryExecuteRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    if not request.approved:
        return {"ok": False, "error": "human_approval_required", "approval_required": True, "state": "planned"}
    wallet_state = await get_wallet(request.wallet_id)
    if not wallet_state:
        return {"ok": False, "error": "wallet_not_found"}
    if wallet_state.get("state") != "active":
        return {"ok": False, "error": "wallet_not_active", "wallet_state": wallet_state.get("state")}

    brief_fields = request.model_dump(exclude={"wallet_id", "approved"})
    service_brief = ServiceUGCFactoryBrief(**brief_fields)
    plan = build_ugc_factory_plan(service_brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}
    estimated_cost = int(plan.get("commercial", {}).get("estimated_generation_cost_cents") or 0)

    # Preflight expensive dependencies before consuming the wallet.
    if not get_media_provider().configured:
        return {"ok": False, "error": "media_provider_not_configured", "state": "preflight_blocked"}
    if not get_asset_storage().configured:
        return {"ok": False, "error": "asset_storage_not_configured", "state": "preflight_blocked"}
    if not get_media_ops().available():
        return {"ok": False, "error": "ffmpeg_not_available", "state": "preflight_blocked"}

    reservation = await reserve_generation(request.wallet_id, estimated_provider_cost_cents=estimated_cost)
    if not reservation.get("ok"):
        return {**reservation, "state": "spend_blocked"}
    reservation["offer_id"] = wallet_state["offer_id"]

    return await execute_ugc_factory_ad(
        service_brief,
        approved=True,
        offer_id=str(wallet_state["offer_id"]),
        reserved_allowance=reservation,
    )


@router.post("/ugc/render")
async def render_ugc_deprecated(_brief: UGCBrief, _=Depends(verify_operator)) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "guarded_factory_required",
        "message": "Paid generation must use /api/studio/ugc/factory/execute with an active server-owned wallet.",
        "paid_generation": False,
    }


@router.post("/ugc/factory/render")
async def render_factory_clip_deprecated(_request: dict[str, Any], _=Depends(verify_operator)) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "guarded_factory_required",
        "message": "Single-clip paid submission is no longer a public surface. Use /api/studio/ugc/factory/execute.",
        "paid_generation": False,
    }


@router.post("/ugc/job")
async def get_render_job(payload: dict[str, str], _=Depends(verify_operator)) -> dict[str, Any]:
    url = payload.get("status_url") or payload.get("response_url") or ""
    return await get_media_provider().fetch_url(url)


@router.get("/social/accounts")
async def social_accounts(_=Depends(verify_operator)) -> dict[str, Any]:
    return await get_publisher().list_accounts()


@router.post("/social/schedule")
async def schedule_social(request: ScheduleRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    if not request.approved:
        return {"ok": False, "error": "human_approval_required"}
    drop = SocialDrop(
        id=request.id,
        content=request.content,
        format=request.format,
        platforms=request.platforms,
        scheduled_at=request.scheduled_at,
        media_urls=request.media_urls,
        approved=request.approved,
        campaign_id=request.campaign_id,
    )
    errors = drop.validate()
    if errors:
        return {"ok": False, "error": "invalid_social_drop", "details": errors}
    return await get_publisher().schedule(PublishRequest(
        content=drop.content,
        platforms=platform_payload(drop),
        scheduled_at=drop.scheduled_at or "",
        approved=drop.approved,
        media_urls=drop.media_urls,
    ))


@router.post("/agent/command")
async def agent_command(payload: AgentCommand, _=Depends(verify_operator)) -> dict[str, Any]:
    intent = parse_voice_intent(payload.command)
    return {
        "ok": True,
        "intent": intent.intent,
        "entity": intent.entity,
        "requires_approval": intent.requires_approval,
        "next": {
            "create_ugc": "/api/studio/ugc/factory/plan",
            "create_campaign": "/api/studio/campaigns/plan",
            "schedule_content": "/api/studio/social/schedule",
            "status": "/api/studio/status",
        }[intent.intent],
    }
