"""Media generation provider boundary for V1.

No model IDs are hardcoded. Fal endpoints are selected with environment
variables so the studio can move between Kling, Seedance, or another provider
without changing campaign or UI code.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


class FalVideoProvider:
    def __init__(self) -> None:
        self.key = os.getenv("FAL_KEY", "")
        self.text_model = os.getenv("FAL_TEXT_VIDEO_MODEL", "")
        self.image_model = os.getenv("FAL_IMAGE_VIDEO_MODEL", "")
        self.queue_base = os.getenv("FAL_QUEUE_URL", "https://queue.fal.run").rstrip("/")

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

        if image_url:
            body: dict[str, Any] = {
                "start_image_url": image_url,
                "prompt": prompt,
                "duration": str(duration),
                "generate_audio": generate_audio,
            }
        else:
            body = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
                "generate_audio": generate_audio,
            }

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

    async def fetch_url(self, url: str) -> dict[str, Any]:
        if not self.key:
            return {"ok": False, "error": "fal_not_configured"}
        if not url.startswith("https://"):
            return {"ok": False, "error": "invalid_fal_url"}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.get(url, headers={"Authorization": f"Key {self.key}"})
            if response.is_error:
                return {"ok": False, "status": response.status_code, "detail": response.text[:800]}
            return {"ok": True, "data": response.json()}


def get_media_provider() -> FalVideoProvider:
    return FalVideoProvider()
