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

    @property
    def within_cost_ceiling(self) -> bool:
        """Mechanical estimate check only; the server wallet remains authoritative."""
        return self.estimated_cost_cents <= self.estimated_cost_ceiling_cents
