"""Provider-neutral UGC ad factory planning and mechanical gates.

This service adapts production patterns from the MIT-licensed MaxFusion AI
OMNI-UGC-AD-FACTORY workflow without depending on MaxFusion, its hosted APIs,
or a specific media model. It performs no network calls and no paid generation.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from .video_prompt import VideoPromptInput, compile_video_prompt


BANNED_DIALOGUE_TERMS = (
    "—",
    "buy now",
    "shop now",
    "link in bio",
    "don't miss",
    "dont miss",
    "miracle",
    "guaranteed",
    "game changer",
    "run don't walk",
    "run dont walk",
)


@dataclass(slots=True)
class UGCFactoryBrief:
    product: str
    audience: str
    pain: str
    mechanism: str
    offer: str = ""
    platform: str = "instagram"
    actor_description: str = "a natural creator speaking like they are sharing something they actually use"
    delivery_tone: str = "calm, honest and direct"
    visual_lane: str = "lane_zero"


def _require(label: str, value: str) -> str:
    clean = " ".join((value or "").split()).strip(" .")
    if not clean:
        raise ValueError(f"{label}_required")
    return clean


def _take_words(value: str, limit: int) -> str:
    clean = " ".join(value.split()).strip(" .")
    return " ".join(clean.split()[:limit])


def _word_count(value: str) -> int:
    return len([word for word in value.split() if word.strip()])


def _money_env(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _default_scripts(*, product: str, pain: str, mechanism: str) -> tuple[str, str]:
    pain_fragment = _take_words(pain, 12)
    product_fragment = _take_words(product, 4)
    mechanism_fragment = _take_words(mechanism, 7)

    clip_1 = (
        f"I kept {pain_fragment}. I thought I could ignore it, but it was getting old. "
        "Same frustration every single time."
    )
    clip_2 = (
        f"I tried {product_fragment} because {mechanism_fragment}. Annoying that I needed it, "
        "but the result is finally repeatable and I can stop thinking about it."
    )
    return clip_1, clip_2


def _gate_scripts(scripts: tuple[str, str]) -> dict[str, Any]:
    counts = [_word_count(script) for script in scripts]
    joined = " ".join(scripts).lower()
    found = [term for term in BANNED_DIALOGUE_TERMS if term in joined]
    checks = [
        {
            "name": "two_clip_contract",
            "passed": len(scripts) == 2,
            "detail": f"clips={len(scripts)}",
        },
        {
            "name": "spoken_word_budget",
            "passed": all(18 <= count <= 32 for count in counts),
            "detail": f"word_counts={counts}",
        },
        {
            "name": "not_an_ad_mechanical_tells",
            "passed": not found,
            "detail": "clear" if not found else f"found={found}",
        },
    ]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _clip_prompt(
    *,
    brief: UGCFactoryBrief,
    script: str,
    clip_number: int,
) -> str:
    if clip_number == 1:
        idea = "Open on the customer's problem and tension. Let the creator sound mid-thought, not like an introduction."
        subject = brief.actor_description
        environment = "a believable everyday setting with imperfect, ordinary details"
        lighting = "soft natural light that can remain consistent into the continuation clip"
        motion = "small unplanned gestures, natural eye-line breaks, and a locked landing at the end"
    else:
        idea = "Continue directly from the supplied seed frame and reveal the product mechanism as a reluctant resolution."
        subject = "the same creator already visible in the supplied seed frame"
        environment = "the exact environment already visible in the supplied seed frame"
        lighting = "the exact lighting already established in the supplied seed frame"
        motion = "continue the prior movement naturally, then finish still with eyes open and mouth closed"

    return compile_video_prompt(
        VideoPromptInput(
            idea=idea,
            product=brief.product,
            camera="stable handheld talking-head framing with no abrupt camera change",
            subject=subject,
            environment=environment,
            lighting=lighting,
            style="realistic",
            motion=motion,
            dialogue=script,
            platform=brief.platform,
            aspect_ratio="9:16",
        )
    )


def _commercial_quote() -> dict[str, Any]:
    price_cents = _money_env("UGC_FACTORY_PRICE_CENTS", 9900)
    clip_cost_cents = _money_env("UGC_FACTORY_CLIP_COST_CENTS", 80)
    expected_clips = _money_env("UGC_FACTORY_EXPECTED_CLIPS_PER_AD", 3, minimum=2)
    estimated_cost = clip_cost_cents * expected_clips
    gross_margin = price_cents - estimated_cost
    gross_margin_pct = round((gross_margin / price_cents * 100), 1) if price_cents else 0.0
    return {
        "billable_unit": "finished_ugc_ad",
        "price_cents": price_cents,
        "estimated_generation_cost_cents": estimated_cost,
        "expected_paid_clip_calls": expected_clips,
        "gross_margin_cents": gross_margin,
        "gross_margin_pct": gross_margin_pct,
        "charges_customer": False,
        "estimate_only": True,
    }


def build_ugc_factory_plan(brief: UGCFactoryBrief) -> dict[str, Any]:
    """Compile one product brief into a gated two-clip production plan."""
    product = _require("product", brief.product)
    audience = _require("audience", brief.audience)
    pain = _require("pain", brief.pain)
    mechanism = _require("mechanism", brief.mechanism)

    normalized = UGCFactoryBrief(
        product=product,
        audience=audience,
        pain=pain,
        mechanism=mechanism,
        offer=" ".join(brief.offer.split()).strip(),
        platform=_require("platform", brief.platform),
        actor_description=_require("actor_description", brief.actor_description),
        delivery_tone=_require("delivery_tone", brief.delivery_tone),
        visual_lane=_require("visual_lane", brief.visual_lane),
    )

    scripts = _default_scripts(product=product, pain=pain, mechanism=mechanism)
    gate = _gate_scripts(scripts)
    clips = [
        {
            "clip": 1,
            "duration_seconds": 10,
            "purpose": "problem_and_tension",
            "script": scripts[0],
            "script_word_count": _word_count(scripts[0]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[0], clip_number=1),
            "seed_from_previous": False,
        },
        {
            "clip": 2,
            "duration_seconds": 10,
            "purpose": "mechanism_and_reluctant_resolution",
            "script": scripts[1],
            "script_word_count": _word_count(scripts[1]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[1], clip_number=2),
            "seed_from_previous": True,
        },
    ]

    return {
        "ok": gate["passed"],
        "factory_version": "ugc-ad-factory-v1",
        "brief": {
            "product": normalized.product,
            "audience": normalized.audience,
            "pain": normalized.pain,
            "mechanism": normalized.mechanism,
            "offer": normalized.offer,
            "platform": normalized.platform,
            "delivery_tone": normalized.delivery_tone,
            "visual_lane": normalized.visual_lane,
        },
        "gate": gate,
        "clips": clips,
        "continuity": {
            "steps": [
                "generate_clip_1",
                "trim_clip_1_tail",
                "extract_final_clean_seed_frame",
                "generate_clip_2_from_seed",
                "seam_check",
                "trim_clip_2_tail",
                "stitch",
            ],
            "seam_threshold_mean_abs_diff": 5 / 255,
            "claim": "planning_contract_only",
        },
        "icm": {
            "template": "icm/_templates/ugc_ad_factory",
            "stages": [
                "01_research",
                "02_script_gate",
                "03_cast",
                "04_generate",
                "05_seam_qa",
                "06_deliver",
            ],
        },
        "commercial": _commercial_quote(),
        "approval_required_before_publish": True,
    }
