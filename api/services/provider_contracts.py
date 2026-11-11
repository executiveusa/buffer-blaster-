"""Provider-neutral UGC generation job boundary.

The contract is intentionally small: provider adapters may translate it to
vendor-specific payloads, while callers retain one stable receipt shape.
Nothing in this module performs network calls or authorizes wallet spend.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from urllib.parse import urlparse

# fal minimax/h3-max reference-to-video (live schema retrieved 2026-11-10):
# reference images + videos + audio clips add up to AT MOST 12 files per
# request. Keyframe stills (image_url/middle/end) and target_audio_url are
# NOT part of that 12-file cap.
MAX_REFERENCE_FILES = 12


def fields_collide(field: str, *others: str) -> bool:
    """True when an env-declared capability field overrides another declared
    field (e.g. the audio-URL field set equal to the boolean generate_audio
    field). Env labels are plumbing, not vendor proof: a colliding
    declaration disables the capability - fail closed."""
    return bool(field) and field in {other for other in others if other}


def reference_list_error(reference_image_urls: list[str] | None, *, max_files: int = MAX_REFERENCE_FILES) -> str | None:
    """Shared preflight for the reference lane, used identically by estimate,
    plan and submit on every adapter: every entry a parsed, valid https URL
    (real host, no embedded credentials) and the combined reference file
    count within the documented 12-file cap. Returns an error code or None."""
    refs = [str(url).strip() for url in (reference_image_urls or []) if str(url).strip()]
    for url in refs:
        if not is_valid_https_url(url):
            return "invalid_reference_url"
    if len(refs) > max_files:
        return "reference_files_cap_exceeded"
    return None


def audio_url_error(audio_url: str | None) -> str | None:
    """Shared parsed-URL validation for a real audio-URL input."""
    if audio_url and not is_valid_https_url(audio_url):
        return "invalid_audio_url"
    return None


def is_valid_https_url(url: str) -> bool:
    """Parse-based https validation: real host required, embedded credentials
    (user:pass@host) rejected - a startswith('https://') prefix check accepts
    both 'https://user:pass@host/x' and hostless strings, so it is not enough."""
    try:
        parsed = urlparse(str(url).strip())
    except (ValueError, AttributeError):
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


from .media_contracts import ApprovalState


ProviderJobState = Literal[
    "planned",
    "submitted",
    "running",
    "finished",
    "failed",
    "cancelled",
    "spend_blocked",
]


class UGCProviderJob(BaseModel):
    """Canonical provider-facing UGC job and durable receipt envelope."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID = Field(default_factory=uuid4)
    plan_id: UUID | None = None
    input_asset_refs: list[UUID] = Field(default_factory=list)
    actor_reference_url: str | None = None
    # Normalized identity reference-asset list for reference-to-video lanes
    # (12 = combined reference images+videos+audio file cap on the fal
    # h3-max reference route, live schema retrieved 2026-11-10). Distinct
    # from actor_reference_url, which stays the scalar start-frame/still.
    reference_image_urls: list[str] = Field(default_factory=list, max_length=12)
    # A real audio URL input (e.g. target_audio_url), distinct from the
    # boolean generate_audio flag below.
    audio_url: str | None = None
    script: str = Field(min_length=1, max_length=12000)
    prompt: str = Field(min_length=1, max_length=24000)
    aspect_ratio: Literal["9:16", "16:9", "1:1", "4:5"] = "9:16"
    duration_seconds: int = Field(default=10, ge=1, le=300)
    generate_audio: bool = True
    provider: str | None = None
    model_name: str | None = None
    estimated_cost_cents: int = Field(default=0, ge=0)
    estimated_cost_ceiling_cents: int = Field(ge=0)
    approval_state: ApprovalState = "draft"
    state: ProviderJobState = "planned"
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    output_receipt: dict[str, Any] = Field(default_factory=dict)
    failure: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("actor_reference_url")
    @classmethod
    def require_https_reference(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("actor_reference_url must use https")
        return value

    @field_validator("reference_image_urls")
    @classmethod
    def require_https_reference_list(cls, value: list[str]) -> list[str]:
        for url in value:
            if not is_valid_https_url(url):
                raise ValueError("every reference_image_urls entry must be a valid https URL without embedded credentials")
        return value

    @field_validator("audio_url")
    @classmethod
    def require_https_audio(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_https_url(value):
            raise ValueError("audio_url must be a valid https URL without embedded credentials")
        return value

    @property
    def within_cost_ceiling(self) -> bool:
        """Mechanical estimate check only; the server wallet remains authoritative."""
        return self.estimated_cost_cents <= self.estimated_cost_ceiling_cents
