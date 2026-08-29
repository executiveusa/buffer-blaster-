"""Agent-first operational API for campaigns, UGC, and social publishing."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.integration_auth import verify_operator
from ..services.media_generation import get_media_provider
from ..services.publishing import PublishRequest, get_publisher
from ..services.social_drop import SocialDrop, platform_payload
from ..services.ugc_factory import UGCFactoryBrief as ServiceUGCFactoryBrief, build_ugc_factory_plan
from ..services.video_prompt import VideoPromptInput, compile_video_prompt
from ..services.voice_intent import parse_voice_intent

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


class RenderRequest(UGCBrief):
    image_url: str | None = None
    duration: str = "10"
    generate_audio: bool = True


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
    angles = [
        "problem and tension",
        "product proof",
        "use case",
        "objection handling",
        "UGC testimonial",
        "offer and urgency",
        "community proof",
    ]
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
        "id": f"campaign-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
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
        "publishing": get_publisher().status(),
        "approval_gate": True,
        "interfaces": ["ui", "rest", "mcp", "cli", "plugin", "voice"],
    }


@router.post("/campaigns/plan")
async def plan_campaign(brief: CampaignBrief, _=Depends(verify_operator)) -> dict[str, Any]:
    return {"ok": True, "plan": _campaign_plan(brief)}


@router.post("/ugc/prompt")
async def create_ugc_prompt(brief: UGCBrief, _=Depends(verify_operator)) -> dict[str, Any]:
    prompt = compile_video_prompt(VideoPromptInput(**brief.model_dump()))
    return {"ok": True, "prompt": prompt, "brief": brief.model_dump()}


@router.post("/ugc/factory/plan")
async def create_ugc_factory_plan(
    brief: UGCFactoryPlanRequest,
    _=Depends(verify_operator),
) -> dict[str, Any]:
    return build_ugc_factory_plan(ServiceUGCFactoryBrief(**brief.model_dump()))


@router.post("/ugc/render")
async def render_ugc(brief: RenderRequest, _=Depends(verify_operator)) -> dict[str, Any]:
    prompt_fields = brief.model_dump(exclude={"image_url", "duration", "generate_audio"})
    prompt = compile_video_prompt(VideoPromptInput(**prompt_fields))
    result = await get_media_provider().submit_video(
        prompt=prompt,
        image_url=brief.image_url,
        duration=brief.duration,
        aspect_ratio=brief.aspect_ratio,
        generate_audio=brief.generate_audio,
    )
    return {"prompt": prompt, **result}


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
            "create_ugc": "/api/studio/ugc/prompt",
            "create_campaign": "/api/studio/campaigns/plan",
            "schedule_content": "/api/studio/social/schedule",
            "status": "/api/studio/status",
        }[intent.intent],
    }
