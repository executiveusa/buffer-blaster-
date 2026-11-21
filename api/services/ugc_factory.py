"""Provider-neutral UGC ad factory planning and mechanical gates.

This service adapts production patterns from the MIT-licensed MaxFusion AI
OMNI-UGC-AD-FACTORY workflow without depending on MaxFusion, its hosted APIs,
or a specific media model. It performs no network calls and no paid generation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
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
    provider_model: str = ""
    # Operator-written dialogue. One line per clip; overrides the generic template.
    scripts: tuple[str, ...] = ()
    # 1 = a single self-contained clip (e.g. a 10 second ad); 2 = seeded continuation.
    clip_count: int = 2
    clip_duration_seconds: int = 10
    # Real product photo (https). Clip 1 renders image-to-video from it so the
    # model copies the real product instead of inventing details.
    product_reference_url: str = ""
    # Exact scene for every clip, e.g. "inside a parked car". Empty keeps the default.
    setting: str = ""
    # Spoken-name guidance, e.g. "Postatees is pronounced POH-stuh-teez".
    pronunciation_notes: str = ""
    # Things the camera must avoid, e.g. "no close-ups of the sleeve lettering".
    avoid: str = ""
    # Text lines for a local ffmpeg end card (no paid generation), e.g. ["Postatees x Mariner", "$70"].
    end_card_lines: tuple[str, ...] = ()
    end_card_seconds: float = 2.0


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


def _word_budget(duration_seconds: int) -> tuple[int, int]:
    """Natural speech is roughly 1.8-3.2 words per second of clip."""
    return max(4, round(duration_seconds * 1.8)), max(6, round(duration_seconds * 3.2))


def _gate_scripts(scripts: tuple[str, ...], *, clip_count: int = 2, duration_seconds: int = 10) -> dict[str, Any]:
    counts = [_word_count(script) for script in scripts]
    joined = " ".join(scripts).lower()
    found = [term for term in BANNED_DIALOGUE_TERMS if term in joined]
    low, high = _word_budget(duration_seconds)
    checks = [
        {"name": "two_clip_contract" if clip_count == 2 else "single_clip_contract", "passed": len(scripts) == clip_count, "detail": f"clips={len(scripts)} expected={clip_count}"},
        {"name": "spoken_word_budget", "passed": all(low <= count <= high for count in counts), "detail": f"word_counts={counts} allowed={low}-{high}"},
        {"name": "not_an_ad_mechanical_tells", "passed": not found, "detail": "clear" if not found else f"found={found}"},
    ]
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _clip_prompt(*, brief: UGCFactoryBrief, script: str, clip_number: int) -> str:
    single = brief.clip_count == 1
    if clip_number == 1:
        if single:
            idea = "One continuous self-contained take. The creator talks straight to camera, mid-thought, and lands the last line cleanly."
        else:
            idea = "Open on the customer's problem and tension. Let the creator sound mid-thought, not like an introduction."
        if brief.product_reference_url:
            idea += " The supplied reference image is the real product: keep its colors, logos and design exactly as shown."
        subject = brief.actor_description
        environment = brief.setting or "a believable everyday setting with imperfect, ordinary details"
        lighting = "soft natural light" if single else "soft natural light that can remain consistent into the continuation clip"
        motion = "small unplanned gestures, natural eye-line breaks, and a locked landing at the end"
    else:
        idea = "Continue directly from the supplied seed frame and reveal the product mechanism as a reluctant resolution."
        subject = "the same creator already visible in the supplied seed frame"
        environment = "the exact environment already visible in the supplied seed frame"
        lighting = "the exact lighting already established in the supplied seed frame"
        motion = "continue the prior movement naturally, then finish still with eyes open and mouth closed"

    notes = [note for note in (brief.pronunciation_notes, f"Avoid: {brief.avoid.rstrip('.')}." if brief.avoid else "") if note]
    if notes:
        idea = f"{idea} {' '.join(notes)}"

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


def _commercial_quote(clip_count: int = 2) -> dict[str, Any]:
    price_cents = _money_env("UGC_FACTORY_PRICE_CENTS", 9900)
    clip_cost_cents = _money_env("UGC_FACTORY_CLIP_COST_CENTS", 80)
    if clip_count == 1:
        # A single clip has no seam retry, so exactly one paid call.
        expected_clips = 1
    else:
        expected_clips = _money_env("UGC_FACTORY_EXPECTED_CLIPS_PER_AD", 3, minimum=2)
    safety_bps = _money_env("UGC_FACTORY_COST_SAFETY_BPS", 12500, minimum=10000)
    raw_estimate = clip_cost_cents * expected_clips
    estimated_cost = math.ceil(raw_estimate * safety_bps / 10_000)
    gross_margin = price_cents - estimated_cost
    gross_margin_pct = round((gross_margin / price_cents * 100), 1) if price_cents else 0.0
    return {
        "billable_unit": "finished_ugc_ad",
        "price_cents": price_cents,
        "raw_generation_estimate_cents": raw_estimate,
        "cost_safety_bps": safety_bps,
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
    if brief.clip_count not in (1, 2):
        raise ValueError("clip_count_must_be_1_or_2")
    duration = int(brief.clip_duration_seconds)
    if not 3 <= duration <= 15:
        raise ValueError("clip_duration_seconds_out_of_range")
    reference = (brief.product_reference_url or "").strip()
    if reference and not reference.startswith("https://"):
        raise ValueError("product_reference_url_must_be_https")
    custom_scripts = tuple(" ".join(line.split()).strip() for line in brief.scripts if line and line.strip())

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
        provider_model=" ".join(brief.provider_model.split()).strip(),
        scripts=custom_scripts,
        clip_count=brief.clip_count,
        clip_duration_seconds=duration,
        product_reference_url=reference,
        setting=" ".join(brief.setting.split()).strip(),
        pronunciation_notes=" ".join(brief.pronunciation_notes.split()).strip(),
        avoid=" ".join(brief.avoid.split()).strip(),
        end_card_lines=tuple(" ".join(line.split()).strip() for line in brief.end_card_lines if line and line.strip()),
        end_card_seconds=max(0.0, min(5.0, float(brief.end_card_seconds))),
    )

    if custom_scripts:
        scripts = custom_scripts
    else:
        scripts = _default_scripts(product=product, pain=pain, mechanism=mechanism)[: brief.clip_count]
    gate = _gate_scripts(scripts, clip_count=brief.clip_count, duration_seconds=duration)
    if len(scripts) != brief.clip_count:
        return {"ok": False, "factory_version": "ugc-ad-factory-v1", "gate": gate, "clips": []}
    clips = [
        {
            "clip": 1,
            "duration_seconds": duration,
            "purpose": "problem_and_tension",
            "script": scripts[0],
            "script_word_count": _word_count(scripts[0]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[0], clip_number=1),
            "seed_from_previous": False,
            "reference_image_url": reference or None,
        },
    ]
    if brief.clip_count == 2:
        clips.append({
            "clip": 2,
            "duration_seconds": duration,
            "purpose": "mechanism_and_reluctant_resolution",
            "script": scripts[1],
            "script_word_count": _word_count(scripts[1]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[1], clip_number=2),
            "seed_from_previous": True,
            "reference_image_url": None,
        })
    continuity_steps = (
        ["generate_clip_1", "trim_clip_1_tail"]
        if brief.clip_count == 1
        else [
            "generate_clip_1",
            "trim_clip_1_tail",
            "extract_final_clean_seed_frame",
            "generate_clip_2_from_seed",
            "seam_check",
            "trim_clip_2_tail",
            "stitch",
        ]
    )
    if normalized.end_card_lines:
        continuity_steps.append("append_end_card")

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
            "provider_model": normalized.provider_model,
            "clip_count": normalized.clip_count,
            "clip_duration_seconds": normalized.clip_duration_seconds,
            "product_reference_url": normalized.product_reference_url,
            "setting": normalized.setting,
            "pronunciation_notes": normalized.pronunciation_notes,
            "avoid": normalized.avoid,
            "end_card_lines": list(normalized.end_card_lines),
            "end_card_seconds": normalized.end_card_seconds,
            "custom_scripts": bool(custom_scripts),
        },
        "gate": gate,
        "clips": clips,
        "continuity": {
            "steps": continuity_steps,
            "seam_threshold_mean_abs_diff": 5 / 255,
            "claim": "execution_implemented_with_bounded_retry",
        },
        "icm": {
            "template": "icm/_templates/ugc_ad_factory",
            "stages": ["01_research", "02_script_gate", "03_cast", "04_generate", "05_seam_qa", "06_deliver"],
        },
        "commercial": _commercial_quote(brief.clip_count),
        "approval_required_before_publish": True,
    }
