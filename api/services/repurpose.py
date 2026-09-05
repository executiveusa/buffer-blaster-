"""Deterministic no-spend long-form to short-form planning.

The service consumes an owned/private source asset reference plus transcript
segments, ranks candidate moments with transparent heuristics, and persists the
plan in the existing canonical creative-job ledger. It never calls an LLM,
media generator, transcription provider, or publishing provider.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .studio_ledger import create_job, get_job


_HOOK_TERMS = {
    "why", "how", "mistake", "secret", "problem", "stop", "never", "before",
    "after", "truth", "changed", "learned", "best", "worst", "surprised",
}
_PROOF_TERMS = {
    "because", "result", "proof", "tested", "measured", "show", "example",
    "percent", "%", "days", "hours", "saved", "grew", "reduced", "increased",
}
_ACTION_TERMS = {"try", "start", "do", "use", "check", "watch", "remember", "step"}


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str = Field(min_length=1, max_length=4000)
    speaker: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class RepurposePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_asset_key: str = Field(min_length=1, max_length=1024)
    source_sha256: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    title: str = Field(default="Long-form source", min_length=1, max_length=255)
    source_duration_seconds: float = Field(gt=0, le=86_400)
    transcript: list[TranscriptSegment] = Field(min_length=1, max_length=5000)
    max_clips: int = Field(default=5, ge=1, le=12)
    target_clip_seconds: int = Field(default=30, ge=10, le=90)
    platform: str = Field(default="short-form", min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")

    @model_validator(mode="after")
    def validate_transcript_bounds(self):
        latest = max(segment.end_seconds for segment in self.transcript)
        if latest > self.source_duration_seconds + 0.25:
            raise ValueError("transcript extends beyond source duration")
        return self


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%']+", text.lower())


def _score(segment: TranscriptSegment) -> tuple[int, list[str]]:
    tokens = _tokens(segment.text)
    unique = set(tokens)
    score = min(len(tokens), 30)
    reasons: list[str] = []

    hook_hits = len(unique & _HOOK_TERMS)
    proof_hits = len(unique & _PROOF_TERMS)
    action_hits = len(unique & _ACTION_TERMS)
    if hook_hits:
        score += hook_hits * 12
        reasons.append("hook_language")
    if proof_hits:
        score += proof_hits * 10
        reasons.append("proof_or_specificity")
    if action_hits:
        score += action_hits * 5
        reasons.append("actionable_language")
    if "?" in segment.text:
        score += 8
        reasons.append("question_tension")
    if any(char.isdigit() for char in segment.text):
        score += 6
        reasons.append("numeric_specificity")
    if 8 <= len(tokens) <= 45:
        score += 5
        reasons.append("short_form_density")
    return score, reasons or ["transcript_density"]


def _window(segment: TranscriptSegment, *, target: int, source_duration: float) -> tuple[float, float]:
    midpoint = (segment.start_seconds + segment.end_seconds) / 2
    half = target / 2
    start = max(0.0, midpoint - half)
    end = min(source_duration, start + target)
    start = max(0.0, end - target)
    return round(start, 3), round(end, 3)


def _overlaps(candidate: tuple[float, float], selected: list[tuple[float, float]]) -> bool:
    start, end = candidate
    for other_start, other_end in selected:
        overlap = max(0.0, min(end, other_end) - max(start, other_start))
        shorter = max(0.001, min(end - start, other_end - other_start))
        if overlap / shorter >= 0.55:
            return True
    return False


def _clip_title(text: str) -> str:
    words = re.sub(r"\s+", " ", text.strip()).split(" ")
    title = " ".join(words[:9]).strip(" .,:;!?")
    return title or "Short-form moment"


def _caption_lines(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text.strip())
    words = clean.split(" ")
    lines: list[str] = []
    for index in range(0, min(len(words), 42), 7):
        lines.append(" ".join(words[index:index + 7]))
    return lines[:6]


def build_repurpose_plan(request: RepurposePlanRequest) -> dict[str, Any]:
    """Build a deterministic ranked short-form plan with zero provider spend."""
    candidates: list[dict[str, Any]] = []
    for index, segment in enumerate(request.transcript):
        score, reasons = _score(segment)
        window = _window(
            segment,
            target=request.target_clip_seconds,
            source_duration=request.source_duration_seconds,
        )
        candidates.append({
            "segment_index": index,
            "score": score,
            "reasons": reasons,
            "window": window,
            "segment": segment,
        })

    candidates.sort(key=lambda item: (-item["score"], item["segment"].start_seconds, item["segment_index"]))
    selected_windows: list[tuple[float, float]] = []
    clips: list[dict[str, Any]] = []
    for candidate in candidates:
        if len(clips) >= request.max_clips:
            break
        window = candidate["window"]
        if _overlaps(window, selected_windows):
            continue
        selected_windows.append(window)
        segment = candidate["segment"]
        clips.append({
            "rank": len(clips) + 1,
            "source_segment_index": candidate["segment_index"],
            "start_seconds": window[0],
            "end_seconds": window[1],
            "duration_seconds": round(window[1] - window[0], 3),
            "score": candidate["score"],
            "score_reasons": candidate["reasons"],
            "title": _clip_title(segment.text),
            "anchor_text": segment.text,
            "caption_lines": _caption_lines(segment.text),
            "crop_instruction": "vertical 9:16; keep active speaker or primary subject centered",
            "b_roll_instruction": "Use source footage first; add only rights-cleared contextual b-roll when it strengthens a proof point.",
            "finish_instruction": "burn readable captions inside mobile-safe bounds; normalize audio; preserve source meaning",
        })

    fingerprint_payload = request.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    plan_id = str(uuid5(NAMESPACE_URL, f"buffer-blaster:repurpose:{request.idempotency_key}"))
    return {
        "plan_id": plan_id,
        "request_fingerprint": fingerprint,
        "source_asset_key": request.source_asset_key,
        "source_sha256": request.source_sha256.lower() if request.source_sha256 else None,
        "source_duration_seconds": request.source_duration_seconds,
        "platform": request.platform,
        "clip_count": len(clips),
        "clips": clips,
        "paid_generation": False,
        "transcription_provider_called": False,
        "generation_provider_called": False,
        "render_required_for_outputs": True,
        "approval_required_before_paid_render": True,
    }


async def create_repurpose_plan(request: RepurposePlanRequest) -> dict[str, Any]:
    plan = build_repurpose_plan(request)
    existing = await get_job(plan["plan_id"])
    if existing:
        existing_fingerprint = (existing.get("input") or {}).get("request_fingerprint")
        if existing_fingerprint != plan["request_fingerprint"]:
            return {"ok": False, "error": "idempotency_conflict", "paid_generation": False}
        return {
            "ok": True,
            "created": False,
            "idempotent_replay": True,
            "job": existing,
            "plan": existing.get("output") or {},
            "paid_generation": False,
        }

    record = await create_job(
        kind="repurpose_plan",
        state="planned",
        job_id=plan["plan_id"],
        input_payload={
            "request": request.model_dump(mode="json"),
            "request_fingerprint": plan["request_fingerprint"],
        },
        output_payload=plan,
        estimated_provider_cost_cents=0,
    )
    if record.get("ledger_error"):
        return {"ok": False, "error": record["ledger_error"], "job": record, "paid_generation": False}
    return {"ok": True, "created": True, "job": record, "plan": plan, "paid_generation": False}


async def get_repurpose_plan(plan_id: str) -> dict[str, Any]:
    record = await get_job(plan_id)
    if not record or record.get("kind") != "repurpose_plan":
        return {"ok": False, "error": "repurpose_plan_not_found"}
    return {"ok": True, "job": record, "plan": record.get("output") or {}, "paid_generation": False}
