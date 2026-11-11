"""Provider-neutral UGC ad factory planning and mechanical gates.

This service adapts production patterns from the MIT-licensed MaxFusion AI
OMNI-UGC-AD-FACTORY workflow without depending on MaxFusion, its hosted APIs,
or a specific media model. It performs no network calls and no paid generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .provider_contracts import MAX_REFERENCE_FILES, is_valid_https_url
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
    casting_reference_url: str = ""
    # Normalized identity reference-asset list (multi-angle / expression stills
    # of the cast creator). Applied to BOTH shots as the provider's
    # reference-image LIST input; the clip-2 continuity seed (trimmed last
    # frame of clip 1) stays a SEPARATE start-frame input. Additive: the
    # scalar casting_reference_url above keeps its existing clip-1 behavior.
    casting_reference_urls: list[str] = field(default_factory=list)
    # Real audio URLs (e.g. narration/voice tracks), one per clip, distinct
    # from the boolean generate_audio flag: these ride the provider's
    # audio-URL input (e.g. target_audio_url), never the boolean field.
    clip_audio_urls: list[str] = field(default_factory=list)


def _require(label: str, value: str) -> str:
    clean = " ".join((value or "").split()).strip(" .")
    if not clean:
        raise ValueError(f"{label}_required")
    return clean


def _take_words(value: str, limit: int) -> str:
    clean = " ".join(value.split()).strip(" .")
    return " ".join(clean.split()[:limit])


def _clean_url_list(values: list[str] | None) -> list[str]:
    """Normalize a URL list: trim entries, drop blanks, preserve order."""
    return [clean for clean in (" ".join(str(url).split()).strip() for url in (values or [])) if clean]


def _clean_audio_slots(values: list[str] | None) -> list[str]:
    """Normalize clip audio URLs WITHOUT dropping blanks: index i is clip i's
    voice slot. Dropping a blank would shift clip 2's voice onto clip 1 -
    slots are preserved, blanks stay empty, never shifted."""
    return [" ".join(str(url).split()).strip() for url in (values or [])]


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


def _gate_scripts(scripts: tuple[str, str], *, casting_reference_url: str = "", casting_reference_urls: list[str] | None = None, clip_audio_urls: list[str] | None = None) -> dict[str, Any]:
    counts = [_word_count(script) for script in scripts]
    joined = " ".join(scripts).lower()
    found = [term for term in BANNED_DIALOGUE_TERMS if term in joined]
    casting_ok = not casting_reference_url or is_valid_https_url(casting_reference_url)
    refs = list(casting_reference_urls or [])
    audios = list(clip_audio_urls or [])
    refs_ok = all(is_valid_https_url(url) for url in refs) and len(refs) <= MAX_REFERENCE_FILES
    # Blank audio slots are allowed (a clip with no pinned voice); only real
    # entries must validate. Slot positions are load-bearing, never shifted.
    audios_ok = all((not url) or is_valid_https_url(url) for url in audios) and len(audios) <= 2
    checks = [
        {"name": "two_clip_contract", "passed": len(scripts) == 2, "detail": f"clips={len(scripts)}"},
        {"name": "spoken_word_budget", "passed": all(18 <= count <= 32 for count in counts), "detail": f"word_counts={counts}"},
        {"name": "not_an_ad_mechanical_tells", "passed": not found, "detail": "clear" if not found else f"found={found}"},
        {
            "name": "casting_reference_url_https",
            "passed": casting_ok,
            "detail": (
                "no_casting_reference"
                if not casting_reference_url
                else ("https_casting_reference_recorded" if casting_ok else "casting_reference_url_must_use_https")
            ),
        },
        {
            "name": "casting_reference_urls_https",
            "passed": refs_ok,
            "detail": (
                f"reference_images={len(refs)}"
                if refs_ok
                else f"every casting_reference_urls entry must be a valid https URL without embedded credentials, at most {MAX_REFERENCE_FILES} files"
            ),
        },
        {
            "name": "clip_audio_urls_https",
            "passed": audios_ok,
            "detail": (
                f"clip_audio_urls={len(audios)}"
                if audios_ok
                else "clip_audio_urls entries must be valid https URLs without embedded credentials, one slot per clip (2); blanks keep their slot"
            ),
        },
    ]
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _clip_prompt(*, brief: UGCFactoryBrief, script: str, clip_number: int, casting_reference_present: bool = False) -> str:
    if clip_number == 1:
        idea = "Open on the customer's problem and tension. Let the creator sound mid-thought, not like an introduction."
        subject = (
            "the creator shown in the supplied casting reference image"
            if casting_reference_present
            else brief.actor_description
        )
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
        casting_reference_url=" ".join(brief.casting_reference_url.split()).strip(),
        casting_reference_urls=_clean_url_list(brief.casting_reference_urls),
        clip_audio_urls=_clean_audio_slots(brief.clip_audio_urls),
    )

    scripts = _default_scripts(product=product, pain=pain, mechanism=mechanism)
    gate = _gate_scripts(
        scripts,
        casting_reference_url=normalized.casting_reference_url,
        casting_reference_urls=normalized.casting_reference_urls,
        clip_audio_urls=normalized.clip_audio_urls,
    )
    clips = [
        {
            "clip": 1,
            "duration_seconds": 10,
            "purpose": "problem_and_tension",
            "script": scripts[0],
            "script_word_count": _word_count(scripts[0]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[0], clip_number=1, casting_reference_present=bool(normalized.casting_reference_url)),
            "seed_from_previous": False,
            "casting_reference_url": normalized.casting_reference_url or None,
            "reference_image_urls": list(normalized.casting_reference_urls),
            "audio_url": (normalized.clip_audio_urls[0] or None) if len(normalized.clip_audio_urls) > 0 else None,
        },
        {
            "clip": 2,
            "duration_seconds": 10,
            "purpose": "mechanism_and_reluctant_resolution",
            "script": scripts[1],
            "script_word_count": _word_count(scripts[1]),
            "prompt": _clip_prompt(brief=normalized, script=scripts[1], clip_number=2),
            "seed_from_previous": True,
            "reference_image_urls": list(normalized.casting_reference_urls),
            "audio_url": (normalized.clip_audio_urls[1] or None) if len(normalized.clip_audio_urls) > 1 else None,
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
            "provider_model": normalized.provider_model,
            "casting_reference_url": normalized.casting_reference_url,
            "casting_reference_urls": list(normalized.casting_reference_urls),
            "clip_audio_urls": list(normalized.clip_audio_urls),
        },
        "gate": gate,
        "casting": {
            "reference_present": bool(normalized.casting_reference_url),
            "applied_to": "clip_1" if normalized.casting_reference_url else None,
            # Scope boundary: one reference still through the provider's scalar
            # image input (image-to-video lane). Multi-reference identity sheets
            # (e.g. reference_image_urls lists on reference-to-video endpoints)
            # and per-shot reference persistence need a provider capability
            # extension; they are NOT implied by this field.
            "mode": "single_reference_still",
            # Normalized identity reference list: applied to BOTH shots through
            # the provider's env-declared reference-images LIST field (a
            # model-specific capability, fail-closed when unconfigured). The
            # clip-2 continuity seed stays a SEPARATE start-frame input.
            "reference_image_urls": list(normalized.casting_reference_urls),
            "reference_list_applied_to": ["clip_1", "clip_2"] if normalized.casting_reference_urls else [],
        },
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
            "claim": "execution_implemented_with_bounded_retry",
        },
        "icm": {
            "template": "icm/_templates/ugc_ad_factory",
            "stages": ["01_research", "02_script_gate", "03_cast", "04_generate", "05_seam_qa", "06_deliver"],
        },
        "commercial": _commercial_quote(),
        "approval_required_before_publish": True,
    }
