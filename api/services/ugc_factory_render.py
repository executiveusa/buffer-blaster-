"""Approval-gated execution for UGC factory clip plans.

This module is intentionally thin: the factory service owns deterministic
planning/gates, while the existing media provider owns model selection and paid
render submission. No provider/model ID is selected here.
"""
from __future__ import annotations

from typing import Any

from .media_generation import get_media_provider
from .ugc_factory import UGCFactoryBrief, build_ugc_factory_plan


async def render_ugc_factory_clip(
    brief: UGCFactoryBrief,
    *,
    clip_number: int = 1,
    approved: bool = False,
    image_url: str | None = None,
) -> dict[str, Any]:
    """Build the current plan, enforce approval, then submit one planned clip."""
    plan = build_ugc_factory_plan(brief)
    if not plan["ok"]:
        return {
            "ok": False,
            "error": "factory_gate_failed",
            "gate": plan["gate"],
            "factory_version": plan["factory_version"],
        }
    if clip_number not in (1, 2):
        return {
            "ok": False,
            "error": "invalid_clip_number",
            "allowed": [1, 2],
            "factory_version": plan["factory_version"],
        }
    if not approved:
        return {
            "ok": False,
            "error": "human_approval_required",
            "approval_required": True,
            "factory_version": plan["factory_version"],
            "clip": clip_number,
            "state": "planned",
        }

    clip = plan["clips"][clip_number - 1]
    result = await get_media_provider().submit_video(
        prompt=clip["prompt"],
        image_url=image_url,
        duration=str(clip["duration_seconds"]),
        aspect_ratio="9:16",
        generate_audio=True,
    )
    if not result.get("ok"):
        return {
            **result,
            "factory_version": plan["factory_version"],
            "clip": clip_number,
            "state": "render_submit_failed",
            "compiled_prompt": clip["prompt"],
        }

    return {
        **result,
        "factory_version": plan["factory_version"],
        "clip": clip_number,
        "state": "render_queued",
        "compiled_prompt": clip["prompt"],
        "script": clip["script"],
        "purpose": clip["purpose"],
        "approval_required_before_publish": True,
    }
