"""Configurable async video gateway adapter.

Supports self-hosted/open-source gateways and hosted aggregators without
hard-coding a vendor. The adapter is intentionally server-owned: credentials,
allowed models, endpoint templates, cost assumptions, and commercial approval
stay in environment configuration.

Compatible shapes include OpenAI-style async video APIs as well as MuAPI-style
submit/poll APIs used by Open-Higgsfield-AI.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urljoin, urlparse

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


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _first_string(payload: Any, keys: tuple[str, ...]) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for container in ("data", "result", "output"):
        nested = payload.get(container)
        found = _first_string(nested, keys)
        if found:
            return found
    return None


class UniversalVideoGatewayProvider:
    """Translate Buffer Blaster's stable media boundary to a configurable gateway."""

    def __init__(self, profile: dict[str, Any] | None = None) -> None:
        self.name = os.getenv("GENERATION_GATEWAY_NAME", "gateway").strip() or "gateway"
        self.base_url = os.getenv("GENERATION_GATEWAY_BASE_URL", "").strip().rstrip("/")
        self.key = os.getenv("GENERATION_GATEWAY_API_KEY", "").strip()
        self.text_model = os.getenv("GENERATION_GATEWAY_TEXT_VIDEO_MODEL", "").strip()
        self.image_model = os.getenv("GENERATION_GATEWAY_IMAGE_VIDEO_MODEL", "").strip() or self.text_model
        self.allowed_models = set(_csv("GENERATION_GATEWAY_ALLOWED_MODELS"))
        self.model_costs = self._load_model_costs()
        self.submit_path = os.getenv("GENERATION_GATEWAY_SUBMIT_PATH", "/v1/videos").strip() or "/v1/videos"
        self.status_path = os.getenv("GENERATION_GATEWAY_STATUS_PATH", "/v1/videos/{id}").strip() or "/v1/videos/{id}"
        self.auth_header = os.getenv("GENERATION_GATEWAY_AUTH_HEADER", "Authorization").strip() or "Authorization"
        self.auth_prefix = os.getenv("GENERATION_GATEWAY_AUTH_PREFIX", "Bearer ").replace("\\n", "\n")
        self.poll_method = os.getenv("GENERATION_GATEWAY_POLL_METHOD", "GET").strip().upper() or "GET"
        self.model_in_body = _bool_env("GENERATION_GATEWAY_MODEL_IN_BODY", True)
        self.image_input_field = os.getenv("GENERATION_GATEWAY_IMAGE_INPUT_FIELD", "image_url").strip() or "image_url"
        self.duration_field = os.getenv("GENERATION_GATEWAY_DURATION_FIELD", "duration").strip() or "duration"
        self.aspect_ratio_field = os.getenv("GENERATION_GATEWAY_ASPECT_RATIO_FIELD", "aspect_ratio").strip() or "aspect_ratio"
        self.audio_field = os.getenv("GENERATION_GATEWAY_AUDIO_FIELD", "generate_audio").strip()
        self.extra_body = self._load_extra_body()
        self.supported_ratios = _csv("GENERATION_GATEWAY_SUPPORTED_RATIOS")
        self.supported_durations_seconds = _int_csv("GENERATION_GATEWAY_SUPPORTED_DURATIONS_SECONDS")
        self.max_reference_images = _int_env("GENERATION_GATEWAY_MAX_REFERENCE_IMAGES", 1 if self.image_model else 0)
        self.default_cost_cents = _int_env("GENERATION_GATEWAY_ESTIMATED_CLIP_COST_CENTS", 0)
        self.estimated_latency_seconds = _int_env("GENERATION_GATEWAY_ESTIMATED_LATENCY_SECONDS", 0) or None
        self.commercial_use_status = os.getenv("GENERATION_GATEWAY_COMMERCIAL_USE_STATUS", "review_required").strip().lower()
        self.deployment = os.getenv("GENERATION_GATEWAY_DEPLOYMENT", "hosted").strip().lower()
        self.lip_sync = _bool_env("GENERATION_GATEWAY_LIP_SYNC")
        self.audio_driven = _bool_env("GENERATION_GATEWAY_AUDIO_DRIVEN")
        self.body_motion = _bool_env("GENERATION_GATEWAY_BODY_MOTION")
        self.quality_rank = _int_env("GENERATION_GATEWAY_QUALITY_RANK", 60)
        self.cost_class = os.getenv("GENERATION_GATEWAY_COST_CLASS", "standard").strip() or "standard"
        self.commercial_use_approved = _bool_env("GENERATION_GATEWAY_COMMERCIAL_USE_APPROVED")

        if profile:
            self._apply_profile(profile)

    def _apply_profile(self, profile: dict[str, Any]) -> None:
        """Apply one server-owned gateway profile without accepting secrets inline."""
        self.name = str(profile.get("name") or self.name).strip() or self.name
        self.base_url = str(profile.get("base_url") or "").strip().rstrip("/")
        api_key_env = str(profile.get("api_key_env") or "").strip()
        self.key = os.getenv(api_key_env, "").strip() if api_key_env else ""
        self.text_model = str(profile.get("text_model") or "").strip()
        self.image_model = str(profile.get("image_model") or "").strip() or self.text_model
        allowed = profile.get("allowed_models")
        self.allowed_models = {str(item).strip() for item in allowed or [] if str(item).strip()}
        costs = profile.get("model_costs_cents")
        self.model_costs = {}
        if isinstance(costs, dict):
            for model, cents in costs.items():
                try:
                    value = int(cents)
                except (TypeError, ValueError):
                    continue
                if str(model).strip() and value >= 0:
                    self.model_costs[str(model).strip()] = value
        self.submit_path = str(profile.get("submit_path") or "/v1/videos").strip() or "/v1/videos"
        self.status_path = str(profile.get("status_path") or "/v1/videos/{id}").strip() or "/v1/videos/{id}"
        self.auth_header = str(profile.get("auth_header") or "Authorization").strip() or "Authorization"
        self.auth_prefix = str(profile.get("auth_prefix") if profile.get("auth_prefix") is not None else "Bearer ")
        self.poll_method = str(profile.get("poll_method") or "GET").strip().upper() or "GET"
        self.model_in_body = bool(profile.get("model_in_body", True))
        self.image_input_field = str(profile.get("image_input_field") or "image_url").strip() or "image_url"
        self.duration_field = str(profile.get("duration_field") or "duration").strip() or "duration"
        self.aspect_ratio_field = str(profile.get("aspect_ratio_field") or "aspect_ratio").strip() or "aspect_ratio"
        self.audio_field = str(profile.get("audio_field") or "generate_audio").strip()
        self.extra_body = profile.get("extra_body") if isinstance(profile.get("extra_body"), dict) else {}
        self.supported_ratios = [str(item) for item in profile.get("supported_ratios", []) if str(item)]
        self.supported_durations_seconds = []
        for item in profile.get("supported_durations_seconds", []):
            try:
                value = int(item)
            except (TypeError, ValueError):
                continue
            if value > 0:
                self.supported_durations_seconds.append(value)
        try:
            self.max_reference_images = max(0, int(profile.get("max_reference_images", 1 if self.image_model else 0)))
        except (TypeError, ValueError):
            self.max_reference_images = 1 if self.image_model else 0
        try:
            self.default_cost_cents = max(0, int(profile.get("estimated_clip_cost_cents", 0)))
        except (TypeError, ValueError):
            self.default_cost_cents = 0
        try:
            latency = int(profile.get("estimated_latency_seconds", 0))
        except (TypeError, ValueError):
            latency = 0
        self.estimated_latency_seconds = latency if latency > 0 else None
        self.commercial_use_status = str(profile.get("commercial_use_status") or "review_required").strip().lower()
        self.deployment = str(profile.get("deployment") or "hosted").strip().lower()
        self.lip_sync = bool(profile.get("lip_sync", False))
        self.audio_driven = bool(profile.get("audio_driven", False))
        self.body_motion = bool(profile.get("body_motion", False))
        try:
            self.quality_rank = max(0, min(100, int(profile.get("quality_rank", 60))))
        except (TypeError, ValueError):
            self.quality_rank = 60
        self.cost_class = str(profile.get("cost_class") or "standard").strip() or "standard"
        self.commercial_use_approved = bool(profile.get("commercial_use_approved", False))

    def _load_model_costs(self) -> dict[str, int]:
        raw = os.getenv("GENERATION_GATEWAY_MODEL_COSTS_JSON", "").strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(value, dict):
            return {}
        costs: dict[str, int] = {}
        for model, cents in value.items():
            try:
                normalized = int(cents)
            except (TypeError, ValueError):
                continue
            if isinstance(model, str) and model.strip() and normalized >= 0:
                costs[model.strip()] = normalized
        return costs

    def _load_extra_body(self) -> dict[str, Any]:
        raw = os.getenv("GENERATION_GATEWAY_EXTRA_BODY_JSON", "").strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.key and (self.text_model or self.image_model))

    def _model(self, *, image_url: str | None, model_name: str | None = None) -> str:
        default_model = (self.image_model if image_url else self.text_model).strip()
        requested = (model_name or "").strip()
        if requested:
            if requested == default_model and not self.allowed_models:
                return requested
            if requested not in self.allowed_models:
                return ""
            return requested
        if not default_model:
            return ""
        if self.allowed_models and default_model not in self.allowed_models:
            return ""
        return default_model

    def estimate_clip_cost_cents(self, model_name: str | None = None, *, image_url: str | None = None) -> int | None:
        model = self._model(image_url=image_url, model_name=model_name)
        if not model:
            return None
        if model in self.model_costs:
            return self.model_costs[model]
        default_model = self.image_model if image_url else self.text_model
        if model == default_model:
            return self.default_cost_cents
        return None

    def _headers(self) -> dict[str, str]:
        return {
            self.auth_header: f"{self.auth_prefix}{self.key}",
            "Content-Type": "application/json",
        }

    def _endpoint(self, template: str, *, model: str = "", request_id: str = "") -> str:
        path = template.replace("{model}", model).replace("{id}", request_id)
        if path.startswith("https://"):
            return path
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _same_origin(self, url: str) -> bool:
        try:
            target = urlparse(url)
            base = urlparse(self.base_url)
        except ValueError:
            return False
        if target.scheme not in {"http", "https"} or base.scheme not in {"http", "https"}:
            return False
        default_target_port = 443 if target.scheme == "https" else 80
        default_base_port = 443 if base.scheme == "https" else 80
        return (
            target.scheme == base.scheme
            and target.hostname == base.hostname
            and (target.port or default_target_port) == (base.port or default_base_port)
        )

    def models(self) -> list[str]:
        models = set(self.allowed_models)
        if self.text_model:
            models.add(self.text_model)
        if self.image_model:
            models.add(self.image_model)
        return sorted(models)

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": self.configured,
            "text_video": bool(self.text_model),
            "image_video": bool(self.image_model),
            "allowed_model_count": len(self.allowed_models),
        }

    def capabilities(self) -> ProviderCapabilities:
        commercial = self.commercial_use_status
        if commercial not in {"approved", "restricted", "review_required", "unknown"}:
            commercial = "unknown"
        deployment = self.deployment
        if deployment not in {"local", "hosted", "hybrid"}:
            deployment = "hosted"
        return ProviderCapabilities(
            provider=self.name,
            text_to_video=bool(self.text_model),
            image_to_video=bool(self.image_model),
            max_reference_images=self.max_reference_images,
            lip_sync=self.lip_sync,
            audio_driven=self.audio_driven,
            body_motion=self.body_motion,
            deployment=deployment,
            supported_ratios=self.supported_ratios,
            supported_durations_seconds=self.supported_durations_seconds,
            estimated_cost_cents=self.estimate_clip_cost_cents() if self.text_model else None,
            estimated_latency_seconds=self.estimated_latency_seconds,
            consent_requirements=["owned_or_licensed_assets", "explicit_person_or_voice_consent"],
            commercial_use_status=commercial,
            health="ready" if self.configured else "unavailable",
        )

    def plan_job(self, job: UGCProviderJob) -> UGCProviderJob:
        model = self._model(image_url=job.actor_reference_url, model_name=job.model_name)
        return job.model_copy(update={
            "provider": self.name,
            "model_name": model or None,
            "estimated_cost_cents": self.estimate_clip_cost_cents(job.model_name, image_url=job.actor_reference_url) or 0,
            "state": "planned",
        })

    async def submit_job(self, job: UGCProviderJob) -> UGCProviderJob:
        planned = self.plan_job(job)
        if planned.approval_state != "approved":
            return planned.model_copy(update={"state": "spend_blocked", "failure": {"error": "approval_required"}})
        if not planned.within_cost_ceiling:
            return planned.model_copy(update={"state": "spend_blocked", "failure": {
                "error": "estimated_cost_exceeds_ceiling",
                "estimated_cost_cents": planned.estimated_cost_cents,
                "estimated_cost_ceiling_cents": planned.estimated_cost_ceiling_cents,
            }})
        if not planned.model_name:
            return planned.model_copy(update={"state": "failed", "failure": {"error": "gateway_model_not_allowed_or_configured"}})

        receipt = await self.submit_video(
            prompt=planned.prompt,
            image_url=planned.actor_reference_url,
            duration=str(planned.duration_seconds),
            aspect_ratio=planned.aspect_ratio,
            generate_audio=planned.generate_audio,
            model_name=planned.model_name,
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
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "generation_gateway_not_configured"}
        model = self._model(image_url=image_url, model_name=model_name)
        if not model:
            return {"ok": False, "error": "gateway_model_not_allowed_or_configured"}

        try:
            duration_seconds = int(duration)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}
        if duration_seconds <= 0:
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration)}

        body: dict[str, Any] = dict(self.extra_body)
        body["prompt"] = prompt
        body[self.duration_field] = duration_seconds
        body[self.aspect_ratio_field] = aspect_ratio
        if self.model_in_body:
            body["model"] = model
        if image_url:
            body[self.image_input_field] = image_url
        if self.audio_field:
            body[self.audio_field] = generate_audio

        endpoint = self._endpoint(self.submit_path, model=model)
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            response = await client.post(endpoint, headers=self._headers(), json=body)
            if response.is_redirect:
                return {"ok": False, "error": "gateway_redirect_rejected", "status": response.status_code}
            if response.is_error:
                return {"ok": False, "error": "gateway_submit_failed", "status": response.status_code, "detail": response.text[:800]}
            data = response.json()

        request_id = _first_string(data, ("id", "request_id", "task_id", "prediction_id"))
        direct_url = _first_string(data, ("video_url", "url"))
        status_url = _first_string(data, ("status_url", "poll_url"))
        response_url = _first_string(data, ("response_url", "result_url"))

        if not status_url and request_id:
            status_url = self._endpoint(self.status_path, model=model, request_id=request_id)
        if not response_url:
            response_url = status_url

        return {
            "ok": True,
            "provider": self.name,
            "model": model,
            "request_id": request_id,
            "status_url": status_url,
            "response_url": response_url,
            "video_url": direct_url,
        }

    async def fetch_url(self, url: str) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "generation_gateway_not_configured"}
        if not self._same_origin(url):
            return {"ok": False, "error": "invalid_gateway_url_origin"}
        if self.poll_method not in {"GET", "POST"}:
            return {"ok": False, "error": "invalid_gateway_poll_method"}
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            if self.poll_method == "POST":
                response = await client.post(url, headers=self._headers(), json={})
            else:
                response = await client.get(url, headers=self._headers())
            if response.is_redirect:
                return {"ok": False, "error": "gateway_redirect_rejected", "status": response.status_code}
            if response.is_error:
                return {"ok": False, "error": "gateway_poll_failed", "status": response.status_code, "detail": response.text[:800]}
            return {"ok": True, "data": response.json()}
