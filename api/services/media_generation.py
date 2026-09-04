"""Media generation provider boundary for Buffer Blaster.

Fal remains the first hosted implementation, but callers can now plan and
submit through a provider-neutral UGC job contract. Model IDs and capability
pricing stay configuration-owned rather than leaking into UI or business logic.
Legacy ``submit_video``/``fetch_url`` methods remain for backwards compatibility.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx

from .media_contracts import ProviderCapabilities
from .provider_contracts import UGCProviderJob


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


def _money_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


class FalVideoProvider:
    def __init__(self) -> None:
        self.key = os.getenv("FAL_KEY", "")
        self.text_model = os.getenv("FAL_TEXT_VIDEO_MODEL", "")
        self.image_model = os.getenv("FAL_IMAGE_VIDEO_MODEL", "")
        self.queue_base = os.getenv("FAL_QUEUE_URL", "https://queue.fal.run").rstrip("/")
        self.image_input_field = os.getenv("FAL_IMAGE_INPUT_FIELD", "image_url").strip() or "image_url"
        self.audio_input_field = os.getenv("FAL_AUDIO_INPUT_FIELD", "").strip()
        self.duration_type = os.getenv("FAL_DURATION_TYPE", "integer").strip().lower() or "integer"
        self.resolution = os.getenv("FAL_VIDEO_RESOLUTION", "").strip()
        self.prompt_expansion_mode = os.getenv("FAL_PROMPT_EXPANSION_MODE", "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.key and (self.text_model or self.image_model))

    def status(self) -> dict[str, Any]:
        return {
            "provider": "fal",
            "configured": self.configured,
            "text_video": bool(self.text_model),
            "image_video": bool(self.image_model),
        }

    def capabilities(self) -> ProviderCapabilities:
        """Return configuration-derived capabilities without exposing secrets."""
        health = "ready" if self.configured else "unavailable"
        commercial = os.getenv("FAL_COMMERCIAL_USE_STATUS", "review_required").strip().lower()
        if commercial not in {"approved", "restricted", "review_required", "unknown"}:
            commercial = "unknown"
        return ProviderCapabilities(
            provider="fal",
            text_to_video=bool(self.text_model),
            image_to_video=bool(self.image_model),
            max_reference_images=1 if self.image_model else 0,
            deployment="hosted",
            supported_ratios=_csv("FAL_SUPPORTED_RATIOS"),
            supported_durations_seconds=_int_csv("FAL_SUPPORTED_DURATIONS_SECONDS"),
            estimated_cost_cents=_money_env("FAL_ESTIMATED_CLIP_COST_CENTS", 80),
            consent_requirements=["owned_or_licensed_assets", "explicit_person_or_voice_consent"],
            commercial_use_status=commercial,
            health=health,
        )

    def plan_job(self, job: UGCProviderJob) -> UGCProviderJob:
        """Bind a neutral job to Fal configuration without spending or calling Fal."""
        model = self.image_model if job.actor_reference_url else self.text_model
        return job.model_copy(
            update={
                "provider": "fal",
                "model_name": model or None,
                "estimated_cost_cents": _money_env("FAL_ESTIMATED_CLIP_COST_CENTS", 80),
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
        if not planned.model_name:
            return planned.model_copy(
                update={"state": "failed", "failure": {"error": "provider_model_not_configured"}}
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
        duration: str = "10",
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
    ) -> dict[str, Any]:
        model = self.image_model if image_url else self.text_model
        if not self.key:
            return {"ok": False, "error": "fal_not_configured", "missing": ["FAL_KEY"]}
        if not model:
            missing = "FAL_IMAGE_VIDEO_MODEL" if image_url else "FAL_TEXT_VIDEO_MODEL"
            return {"ok": False, "error": "fal_model_not_configured", "missing": [missing]}

        try:
            duration_seconds = int(duration)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}
        if duration_seconds <= 0:
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}
        if self.duration_type not in {"integer", "string"}:
            return {"ok": False, "error": "invalid_fal_duration_type", "duration_type": self.duration_type}
        duration_value: int | str = str(duration_seconds) if self.duration_type == "string" else duration_seconds

        body: dict[str, Any] = {
            "prompt": prompt,
            "duration": duration_value,
        }
        if image_url:
            body[self.image_input_field] = image_url
        else:
            body["aspect_ratio"] = aspect_ratio
        if self.audio_input_field:
            body[self.audio_input_field] = generate_audio
        if self.resolution:
            body["resolution"] = self.resolution
        if self.prompt_expansion_mode:
            body["prompt_expansion_mode"] = self.prompt_expansion_mode

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{self.queue_base}/{model}",
                headers={"Authorization": f"Key {self.key}", "Content-Type": "application/json"},
                json=body,
            )
            if response.is_error:
                return {
                    "ok": False,
                    "error": "fal_submit_failed",
                    "status": response.status_code,
                    "detail": response.text[:800],
                }
            data = response.json()

        return {
            "ok": True,
            "provider": "fal",
            "model": model,
            "request_id": data.get("request_id"),
            "status_url": data.get("status_url"),
            "response_url": data.get("response_url"),
            "cancel_url": data.get("cancel_url"),
        }

    def _is_queue_url(self, url: str) -> bool:
        try:
            target = urlparse(url)
            queue = urlparse(self.queue_base)
        except ValueError:
            return False
        return (
            target.scheme == "https"
            and queue.scheme == "https"
            and target.hostname == queue.hostname
            and (target.port or 443) == (queue.port or 443)
        )

    async def fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch a Fal queue/status response without leaking the Fal key.

        The Authorization header is only ever sent to the exact configured Fal
        queue origin. Asset URLs from provider responses are intentionally not
        accepted here; the executor downloads those separately without this key.
        """
        if not self.key:
            return {"ok": False, "error": "fal_not_configured"}
        if not self._is_queue_url(url):
            return {"ok": False, "error": "invalid_fal_url_origin"}
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            response = await client.get(url, headers={"Authorization": f"Key {self.key}"})
            if response.is_redirect:
                return {"ok": False, "error": "fal_redirect_rejected", "status": response.status_code}
            if response.is_error:
                return {"ok": False, "status": response.status_code, "detail": response.text[:800]}
            return {"ok": True, "data": response.json()}


def get_media_provider() -> FalVideoProvider:
    return FalVideoProvider()
