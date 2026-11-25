"""Sand.ai (MAGI-2) video provider adapter for Buffer Blaster.

Optional third adapter behind the existing provider boundary. Selected with
``ACTIVE_MEDIA_PROVIDER=sand``; Fal remains the default. Everything about the
vendor stays configuration-owned: key, model allowlist, per-second pricing,
commercial approval state.

Sand native API (docs: https://platform.sand.ai/docs/api-reference/):
- POST {base}/v2/generations with model, parts[], duration, aspectRatio.
- GET  {base}/v2/generations/{id} to poll; status queued|processing|
  succeeded|failed|canceled; output.videoUrl on success.
- Reference media can be passed as a public HTTPS url directly in parts, so
  no asset upload is needed for URL-based references.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx

from .media_contracts import ProviderCapabilities
from .provider_contracts import UGCProviderJob

DEFAULT_BASE_URL = "https://api.sand.ai"
DEFAULT_MODEL = "magi-2"
DEFAULT_COST_PER_SECOND_CENTS = 8  # $0.08/s per Sand model-pricing docs


def _csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def _int_csv(name: str) -> list[int]:
    values: list[int] = []
    for raw in _csv(name):
        try:
            value = int(raw)
        except ValueError:
            continue
        if value > 0:
            values.append(value)
    return values


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


class SandVideoProvider:
    def __init__(self) -> None:
        self.key = os.getenv("SAND_API_KEY", "").strip()
        self.base_url = os.getenv("SAND_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL
        self.model = os.getenv("SAND_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        self.allowed_models = set(_csv("SAND_ALLOWED_MODELS")) or {self.model}
        self.cost_per_second_cents = _int_env("SAND_COST_PER_SECOND_CENTS", DEFAULT_COST_PER_SECOND_CENTS)
        self.default_duration_seconds = _int_env("SAND_DEFAULT_DURATION_SECONDS", 5)
        self.supported_ratios = _csv("SAND_SUPPORTED_RATIOS") or ["9:16", "16:9", "1:1"]
        self.supported_durations = _int_csv("SAND_SUPPORTED_DURATIONS_SECONDS") or [5, 10]
        self.max_reference_images = _int_env("SAND_MAX_REFERENCE_IMAGES", 1)
        self.enhance_prompt = os.getenv("SAND_ENHANCE_PROMPT", "").strip().lower()

    @property
    def configured(self) -> bool:
        return bool(self.key)

    def models(self) -> list[str]:
        return sorted(self.allowed_models)

    def estimate_clip_cost_cents(
        self,
        model_name: str | None = None,
        *,
        image_url: str | None = None,
        duration_seconds: int | None = None,
    ) -> int | None:
        if model_name and model_name not in self.allowed_models:
            return None
        seconds = duration_seconds or self.default_duration_seconds
        return self.cost_per_second_cents * seconds

    def status(self) -> dict[str, Any]:
        return {
            "provider": "sand",
            "configured": self.configured,
            "model": self.model,
            "allowed_models": self.models(),
        }

    def capabilities(self) -> ProviderCapabilities:
        health = "ready" if self.configured else "unavailable"
        commercial = os.getenv("SAND_COMMERCIAL_USE_STATUS", "review_required").strip().lower()
        if commercial not in {"approved", "restricted", "review_required", "unknown"}:
            commercial = "unknown"
        return ProviderCapabilities(
            provider="sand",
            text_to_video=True,
            image_to_video=True,
            max_reference_images=self.max_reference_images,
            deployment="hosted",
            supported_ratios=self.supported_ratios,
            supported_durations_seconds=self.supported_durations,
            estimated_cost_cents=self.estimate_clip_cost_cents(),
            consent_requirements=["owned_or_licensed_assets", "explicit_person_or_voice_consent"],
            commercial_use_status=commercial,
            health=health,
        )

    def plan_job(self, job: UGCProviderJob) -> UGCProviderJob:
        """Bind a neutral job to Sand configuration without spending or calling Sand."""
        return job.model_copy(
            update={
                "provider": "sand",
                "model_name": self.model,
                "estimated_cost_cents": self.cost_per_second_cents * job.duration_seconds,
                "state": "planned",
            }
        )

    async def submit_job(self, job: UGCProviderJob) -> UGCProviderJob:
        """Submit only a contract-approved job that remains inside its cost ceiling."""
        planned = self.plan_job(job)
        if planned.approval_state != "approved":
            return planned.model_copy(
                update={"state": "spend_blocked", "failure": {"error": "approval_required"}}
            )
        if not planned.within_cost_ceiling:
            return planned.model_copy(
                update={
                    "state": "spend_blocked",
                    "failure": {
                        "error": "estimated_cost_exceeds_ceiling",
                        "estimated_cost_cents": planned.estimated_cost_cents,
                        "estimated_cost_ceiling_cents": planned.estimated_cost_ceiling_cents,
                    },
                }
            )
        receipt = await self.submit_video(
            prompt=planned.prompt,
            image_url=planned.actor_reference_url,
            duration=str(planned.duration_seconds),
            aspect_ratio=planned.aspect_ratio,
            generate_audio=planned.generate_audio,
        )
        if not receipt.get("ok"):
            return planned.model_copy(update={"state": "failed", "failure": dict(receipt)})
        return planned.model_copy(update={"state": "submitted", "output_receipt": dict(receipt), "failure": {}})

    async def submit_video(
        self,
        *,
        prompt: str,
        image_url: str | None = None,
        duration: str = "5",
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if model_name and model_name not in self.allowed_models:
            return {"ok": False, "error": "sand_model_not_allowed", "model": model_name}
        if not self.key:
            return {"ok": False, "error": "sand_not_configured", "missing": ["SAND_API_KEY"]}
        try:
            duration_seconds = int(duration)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}
        if duration_seconds <= 0:
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}

        parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        if image_url:
            if not image_url.startswith("https://"):
                return {"ok": False, "error": "sand_reference_requires_https"}
            parts.append({"type": "reference_image", "image": {"url": image_url}})

        body: dict[str, Any] = {
            "model": self.model,
            "parts": parts,
            "duration": duration_seconds,
            "aspectRatio": aspect_ratio,
            "generateAudio": generate_audio,
        }
        if self.enhance_prompt in {"true", "false"}:
            body["enhancePrompt"] = self.enhance_prompt == "true"

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{self.base_url}/v2/generations",
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=body,
            )
            if response.is_error:
                return {
                    "ok": False,
                    "error": "sand_submit_failed",
                    "status": response.status_code,
                    "detail": response.text[:800],
                }
            data = response.json()

        generation_id = data.get("id")
        return {
            "ok": True,
            "provider": "sand",
            "model": self.model,
            "request_id": str(generation_id) if generation_id is not None else None,
            "status_url": f"{self.base_url}/v2/generations/{generation_id}" if generation_id is not None else None,
            "status": data.get("status"),
        }

    def _is_sand_url(self, url: str) -> bool:
        try:
            target = urlparse(url)
            base = urlparse(self.base_url)
        except ValueError:
            return False
        return (
            target.scheme == "https"
            and base.scheme == "https"
            and target.hostname == base.hostname
            and (target.port or 443) == (base.port or 443)
        )

    async def fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch a Sand generation status/response without leaking the key.

        The Authorization header is only ever sent to the exact configured Sand
        origin. output.videoUrl downloads are signed and need no key; the
        executor downloads those separately like it does for Fal assets.
        """
        if not self.key:
            return {"ok": False, "error": "sand_not_configured"}
        if not self._is_sand_url(url):
            return {"ok": False, "error": "invalid_sand_url_origin"}
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {self.key}"})
            if response.is_redirect:
                return {"ok": False, "error": "sand_redirect_rejected", "status": response.status_code}
            if response.is_error:
                return {"ok": False, "status": response.status_code, "detail": response.text[:800]}
            return {"ok": True, "data": response.json()}
