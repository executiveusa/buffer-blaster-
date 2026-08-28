"""Provider-neutral prompt compiler for short-form product video.

The compiler intentionally follows the universal structure in the owner's
video-prompting guide: scene -> camera -> subject -> environment -> lighting
and style -> motion -> optional dialogue. It does not select a model.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VideoPromptInput:
    idea: str
    camera: str = "stable handheld medium shot with one smooth push-in"
    subject: str = "a natural creator demonstrating the product"
    environment: str = "a believable everyday setting"
    lighting: str = "soft natural light"
    style: str = "realistic"
    motion: str = "small continuous movements with natural pacing"
    dialogue: str | None = None
    product: str | None = None
    platform: str = "instagram"
    aspect_ratio: str = "9:16"


def _one_style(value: str) -> str:
    """Keep the first visual style to avoid conflicting style stacks."""
    first = (value or "realistic").split(",", 1)[0].strip()
    return first or "realistic"


def compile_video_prompt(brief: VideoPromptInput) -> str:
    idea = brief.idea.strip() or "A creator demonstrates a product."
    product_line = f" Product focus: {brief.product.strip()}." if brief.product else ""
    sections = [
        f"SCENE: {idea}{product_line}",
        f"CAMERA: {brief.camera.strip()}. Composition {brief.aspect_ratio} for {brief.platform}.",
        f"SUBJECT: {brief.subject.strip()}.",
        f"ENVIRONMENT: {brief.environment.strip()}.",
        f"LIGHTING & STYLE: {brief.lighting.strip()}; {_one_style(brief.style)}.",
        f"MOTION: {brief.motion.strip()}. Keep the action continuous and physically plausible.",
    ]
    if brief.dialogue and brief.dialogue.strip():
        sections.append(f'DIALOGUE: "{brief.dialogue.strip()}" Spoken naturally, not like a staged sales read.')
    sections.append("QUALITY: Preserve product identity, readable packaging, natural hands, consistent subject identity, and believable physics. Avoid excessive cuts, overacting, warped text, duplicate objects, and abrupt camera changes.")
    return "\n".join(sections)
