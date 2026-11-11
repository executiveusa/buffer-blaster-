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
from .provider_contracts import MAX_REFERENCE_FILES, UGCProviderJob, audio_url_error, fields_collide, reference_list_error
from .universal_media_gateway import UniversalVideoGatewayProvider


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
        # This field carries the boolean generate_audio flag only. It is NOT an
        # audio-URL hook: renaming it (e.g. to target_audio_url) would send
        # "true", not narration audio. Voice/TTS audio input needs a separate
        # capability contract, not an env rename.
        self.audio_input_field = os.getenv("FAL_AUDIO_INPUT_FIELD", "").strip()
        self.duration_type = os.getenv("FAL_DURATION_TYPE", "integer").strip().lower() or "integer"
        self.resolution = os.getenv("FAL_VIDEO_RESOLUTION", "").strip()
        self.prompt_expansion_mode = os.getenv("FAL_PROMPT_EXPANSION_MODE", "").strip()
        # Model-specific capabilities, env-declared and fail-closed - never env
        # renames of the scalar/boolean fields above:
        # - FAL_REFERENCE_VIDEO_MODEL + FAL_REFERENCE_IMAGES_FIELD: a
        #   reference-to-video model whose reference input is a LIST (e.g.
        #   reference_image_urls on minimax/h3-max/reference-to-video). The
        #   scalar FAL_IMAGE_INPUT_FIELD cannot carry that list.
        # - FAL_AUDIO_URL_FIELD: a real https audio-URL input (e.g.
        #   target_audio_url), distinct from the boolean generate_audio flag.
        self.reference_model = os.getenv("FAL_REFERENCE_VIDEO_MODEL", "").strip()
        self.reference_images_field = os.getenv("FAL_REFERENCE_IMAGES_FIELD", "").strip()
        self.audio_url_field = os.getenv("FAL_AUDIO_URL_FIELD", "").strip()
        # Field-collision guards: env field NAMES are not route capabilities.
        # If the operator points the reference-LIST field at the scalar image
        # field (or the audio-URL field at the boolean flag), the body would
        # silently override one input with another. Colliding declarations
        # disable the capability - fail closed, never an override.
        self._refs_field_collision = fields_collide(self.reference_images_field, self.image_input_field, self.audio_input_field)
        self._audio_field_collision = fields_collide(self.audio_url_field, self.audio_input_field, self.image_input_field, self.reference_images_field)
        # Route allowlist for the audio-URL field: an env field NAME is not
        # proof the selected route accepts it. Audio URLs are sent only on
        # models the operator explicitly declares here (doc-verified example
        # as of 2026-11-10: minimax/h3-max text/image/reference routes all
        # document target_audio_url - re-verify before extending).
        self.audio_url_models = set(_csv("FAL_AUDIO_URL_MODELS"))

    def _reference_capability(self) -> tuple[bool, list[str]]:
        """Reference lane is usable only with model + disjoint list field +
        the route-required prompt expansion mode (live schema 2026-11-10:
        prompt_expansion_mode is REQUIRED on reference-to-video)."""
        missing = [name for name, value in (
            ("FAL_REFERENCE_VIDEO_MODEL", self.reference_model),
            ("FAL_REFERENCE_IMAGES_FIELD", self.reference_images_field),
            ("FAL_PROMPT_EXPANSION_MODE", self.prompt_expansion_mode),
        ) if not value]
        if self._refs_field_collision and "FAL_REFERENCE_IMAGES_FIELD" not in missing:
            missing.append("FAL_REFERENCE_IMAGES_FIELD disjoint from FAL_IMAGE_INPUT_FIELD/FAL_AUDIO_INPUT_FIELD")
        return (not missing, missing)

    def _audio_url_capability(self, model: str | None = None) -> tuple[bool, list[str]]:
        if not self.audio_url_field:
            return False, ["FAL_AUDIO_URL_FIELD"]
        if self._audio_field_collision:
            return False, ["FAL_AUDIO_URL_FIELD disjoint from FAL_AUDIO_INPUT_FIELD/FAL_IMAGE_INPUT_FIELD/FAL_REFERENCE_IMAGES_FIELD"]
        if model is not None and model not in self.audio_url_models:
            return False, ["FAL_AUDIO_URL_MODELS to include the selected route"]
        return True, []

    @property
    def configured(self) -> bool:
        return bool(self.key and (self.text_model or self.image_model))

    def models(self) -> list[str]:
        return sorted({model for model in (self.text_model, self.image_model, self.reference_model) if model})

    def estimate_clip_cost_cents(self, model_name: str | None = None, *, image_url: str | None = None, reference_image_urls: list[str] | None = None, audio_url: str | None = None) -> int | None:
        refs = [str(url) for url in (reference_image_urls or []) if str(url).strip()]
        if refs:
            # The reference lane is a different model with a list input; an
            # unconfigured, invalid, or over-cap capability cannot be priced,
            # so it fails closed.
            capable, _ = self._reference_capability()
            if not capable or reference_list_error(refs) is not None:
                return None
            configured_model = self.reference_model
        else:
            configured_model = self.image_model if image_url else self.text_model
        if audio_url:
            capable, _ = self._audio_url_capability(configured_model)
            if not capable or audio_url_error(audio_url) is not None:
                return None
        if model_name and model_name != configured_model:
            return None
        return _money_env("FAL_ESTIMATED_CLIP_COST_CENTS", 80) if configured_model else None

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
            # 12 = verified reference-file cap on the fal reference-to-video
            # lane (live docs, 2026-11-10); 1 = scalar image-to-video still.
            max_reference_images=(MAX_REFERENCE_FILES if self._reference_capability()[0] else (1 if self.image_model else 0)),
            deployment="hosted",
            supported_ratios=_csv("FAL_SUPPORTED_RATIOS"),
            supported_durations_seconds=_int_csv("FAL_SUPPORTED_DURATIONS_SECONDS"),
            estimated_cost_cents=self.estimate_clip_cost_cents() if self.text_model else None,
            consent_requirements=["owned_or_licensed_assets", "explicit_person_or_voice_consent"],
            commercial_use_status=commercial,
            health=health,
        )

    def plan_job(self, job: UGCProviderJob) -> UGCProviderJob:
        """Bind a neutral job to Fal configuration without spending or calling Fal.
        Jobs carrying reference/audio inputs the configured capabilities cannot
        serve fail EXPLICITLY here - their inputs are never silently dropped."""
        refs = list(job.reference_image_urls or [])
        model = self.reference_model if refs else (self.image_model if job.actor_reference_url else self.text_model)
        estimate = self.estimate_clip_cost_cents(
            model, image_url=job.actor_reference_url,
            reference_image_urls=refs or None, audio_url=job.audio_url,
        )
        if estimate is None:
            return job.model_copy(update={
                "provider": "fal",
                "model_name": None,
                "estimated_cost_cents": 0,
                "state": "failed",
                "failure": {"error": "fal_capability_not_configured_for_job_inputs", "charge_outcome": "not_sent"},
            })
        return job.model_copy(
            update={
                "provider": "fal",
                "model_name": model or None,
                "estimated_cost_cents": estimate,
                "state": "planned",
            }
        )

    async def submit_job(self, job: UGCProviderJob) -> UGCProviderJob:
        """Submit only a contract-approved job that remains inside its cost ceiling."""
        planned = self.plan_job(job)
        if planned.state == "failed":
            return planned
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
            reference_image_urls=list(planned.reference_image_urls) or None,
            audio_url=planned.audio_url,
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
        reference_image_urls: list[str] | None = None,
        audio_url: str | None = None,
    ) -> dict[str, Any]:
        # Every ok:false return carries a typed charge_outcome so settlement
        # never has to guess whether the provider could have billed the call:
        #   "not_sent"           - local pre-send validation; no HTTP request
        #                          was made, so the call is DEFINITELY uncharged.
        #   "rejected_uncharged" - a vendor-DOCUMENTED uncharged reject. fal's
        #                          model docs (retrieved 2026-11-10) document no
        #                          such class for queue submits, so this adapter
        #                          never emits it until a cited doc says so.
        #   "unknown_after_send" - the request WAS sent (an HTTP response or an
        #                          ambiguous transport state exists); whether the
        #                          provider billed it is unknown. Conservatively
        #                          settled as estimated exposure, never zero.
        refs = [str(url) for url in (reference_image_urls or []) if str(url).strip()]
        if refs:
            capable, missing = self._reference_capability()
            if not capable:
                return {"ok": False, "error": "fal_reference_images_not_configured", "missing": missing, "charge_outcome": "not_sent"}
            # Live schema (2026-11-10): reference images+videos+audio add up to
            # at most 12 files per request. The scalar keyframe seed and target
            # audio are not documented as counting toward that cap.
            ref_error = reference_list_error(refs)
            if ref_error == "invalid_reference_url":
                return {"ok": False, "error": "fal_invalid_reference_url", "charge_outcome": "not_sent"}
            if ref_error == "reference_files_cap_exceeded":
                return {"ok": False, "error": "fal_reference_files_cap_exceeded", "reference_files": len(refs), "cap": MAX_REFERENCE_FILES, "charge_outcome": "not_sent"}
            configured_model = self.reference_model
        else:
            configured_model = self.image_model if image_url else self.text_model
        if audio_url:
            capable, missing = self._audio_url_capability(configured_model)
            if not capable:
                return {"ok": False, "error": "fal_audio_url_not_configured", "missing": missing, "charge_outcome": "not_sent"}
            if audio_url_error(audio_url) is not None:
                return {"ok": False, "error": "fal_invalid_audio_url", "charge_outcome": "not_sent"}
        if model_name and model_name != configured_model:
            return {"ok": False, "error": "fal_model_override_not_allowed", "model": model_name, "charge_outcome": "not_sent"}
        model = configured_model
        if not self.key:
            return {"ok": False, "error": "fal_not_configured", "missing": ["FAL_KEY"], "charge_outcome": "not_sent"}
        if not model:
            missing = "FAL_IMAGE_VIDEO_MODEL" if image_url else "FAL_TEXT_VIDEO_MODEL"
            return {"ok": False, "error": "fal_model_not_configured", "missing": [missing], "charge_outcome": "not_sent"}

        try:
            duration_seconds = int(duration)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration), "charge_outcome": "not_sent"}
        if duration_seconds <= 0:
            return {"ok": False, "error": "invalid_video_duration", "duration": str(duration), "charge_outcome": "not_sent"}
        if self.duration_type not in {"integer", "string"}:
            return {"ok": False, "error": "invalid_fal_duration_type", "duration_type": self.duration_type, "charge_outcome": "not_sent"}
        if audio_url and duration_seconds < 2:
            # Documented constraint: output must run at least 2 s with
            # target_audio_url (live schema 2026-11-10).
            return {"ok": False, "error": "fal_audio_duration_too_short", "duration": duration_seconds, "charge_outcome": "not_sent"}
        duration_value: int | str = str(duration_seconds) if self.duration_type == "string" else duration_seconds

        body: dict[str, Any] = {
            "prompt": prompt,
            "duration": duration_value,
        }
        if image_url:
            # The start-frame (continuity seed) stays a SEPARATE scalar input
            # even when identity references are present.
            body[self.image_input_field] = image_url
        else:
            body["aspect_ratio"] = aspect_ratio
        if refs:
            body[self.reference_images_field] = refs
        if audio_url:
            # A real audio URL on its own env-declared field; the boolean
            # generate_audio flag below is untouched by it.
            body[self.audio_url_field] = audio_url
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
                # An HTTP error response means the request reached the service:
                # a 500/502 (or any status) AFTER send is unknown-after-send,
                # never a definite zero.
                return {
                    "ok": False,
                    "error": "fal_submit_failed",
                    "status": response.status_code,
                    "detail": response.text[:800],
                    "charge_outcome": "unknown_after_send",
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


def get_media_provider() -> FalVideoProvider | UniversalVideoGatewayProvider:
    """Return the active server-owned media adapter.

    ACTIVE_MEDIA_PROVIDER=fal keeps the existing implementation.
    ACTIVE_MEDIA_PROVIDER=gateway (or muapi/open_higgsfield) enables the
    configurable async gateway adapter, which can target self-hosted gateways
    or compatible hosted aggregators without changing Buffer Blaster business logic.
    """
    selected = (os.getenv("ACTIVE_MEDIA_PROVIDER", "fal") or "fal").strip().lower()
    if selected in {"gateway", "universal", "muapi", "open_higgsfield", "open-higgsfield"}:
        return UniversalVideoGatewayProvider()
    return FalVideoProvider()
