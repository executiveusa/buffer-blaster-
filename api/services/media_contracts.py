"""Provider-neutral canonical media contracts for Buffer Blaster UGC receipts.

These contracts describe sources, strategy, plans, takes, and provider
capabilities. They do not select or invoke a renderer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _now() -> datetime:
    return datetime.now(timezone.utc)


SourceKind = Literal[
    "product_image",
    "creator_image",
    "reference_ad",
    "source_video",
    "source_audio",
    "brand_asset",
    "url",
]
RightsState = Literal["owned", "licensed", "authorized_analysis", "restricted", "unknown"]
ConsentState = Literal["not_applicable", "pending", "granted", "denied"]
ApprovalState = Literal["draft", "pending", "approved", "rejected"]
FinishMode = Literal["raw_ugc", "creator_premium", "product_cinematic", "editorial_brand"]
ProviderPreference = Literal["auto", "fast", "premium", "sovereign"]


class CreativeSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    client_id: UUID | None = None
    kind: SourceKind
    uri: str | None = None
    storage_key: str | None = None
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    mime_type: str = Field(min_length=1, max_length=255)
    owner: str = Field(min_length=1, max_length=255)
    rights_state: RightsState
    consent_state: ConsentState = "not_applicable"
    provider_export_allowed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("sha256")
    @classmethod
    def normalize_hash(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def validate_source_boundary(self) -> "CreativeSource":
        if not self.uri and not self.storage_key:
            raise ValueError("creative source requires uri or storage_key")
        if self.kind in {"creator_image", "source_audio"} and self.consent_state == "not_applicable":
            raise ValueError("creator/voice source requires explicit consent_state")
        if self.provider_export_allowed and self.consent_state == "denied":
            raise ValueError("provider export cannot be allowed when consent is denied")
        return self


class StrategyReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    client_id: UUID | None = None
    source_refs: list[UUID] = Field(min_length=1)
    source_hashes: list[str] = Field(default_factory=list)
    hook_mechanic: str = ""
    angle: str = ""
    customer_tension: str = ""
    narrative_structure: str = ""
    pacing: str = ""
    creator_archetype: str = ""
    proof_device: str = ""
    shot_logic: list[dict[str, Any]] = Field(default_factory=list)
    cta_mechanic: str = ""
    claims_brand_risks: list[str] = Field(default_factory=list)
    originality_transformations: list[str] = Field(default_factory=list)
    recommended_test_variable: str = ""
    model_provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class UGCPlanDraft(BaseModel):
    """External no-spend plan input; workspace identity is injected server-side."""

    model_config = ConfigDict(extra="forbid")

    client_id: UUID | None = None
    product_source_refs: list[UUID] = Field(min_length=1)
    creator_source_ref: UUID | None = None
    setting_style_refs: list[UUID] = Field(default_factory=list)
    strategy_receipt_ref: UUID | None = None
    script: str = Field(min_length=1, max_length=12000)
    shot_plan: list[dict[str, Any]] = Field(min_length=1)
    aspect_ratio: Literal["9:16", "16:9", "1:1", "4:5"] = "9:16"
    duration_seconds: int = Field(default=10, ge=1, le=300)
    finish_mode: FinishMode = "raw_ugc"
    provider_preference: ProviderPreference = "auto"
    estimated_cost_ceiling_cents: int = Field(ge=0)
    approval_state: ApprovalState = "draft"
    consent_rights_refs: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rights_boundary(self) -> "UGCPlanDraft":
        if self.creator_source_ref is not None and not self.consent_rights_refs:
            raise ValueError("creator_source_ref requires at least one consent_rights_ref")
        return self


class UGCPlan(UGCPlanDraft):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class MediaTake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    take_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    plan_id: UUID
    parent_take_id: UUID | None = None
    source_refs: list[UUID] = Field(default_factory=list)
    provider: str = Field(min_length=1, max_length=128)
    model_name: str = Field(min_length=1, max_length=255)
    model_version: str | None = None
    request_job_id: str | None = None
    actual_cost_cents: int = Field(default=0, ge=0)
    output_storage_key: str | None = None
    artifact_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_seconds: float | None = Field(default=None, ge=0)
    derivation_state: Literal["generated", "derived"] = "generated"
    finish_state: Literal["raw", "processing", "finished", "failed"] = "raw"
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    text_to_video: bool = False
    image_to_video: bool = False
    max_reference_images: int = Field(default=0, ge=0)
    lip_sync: bool = False
    audio_driven: bool = False
    body_motion: bool = False
    deployment: Literal["local", "hosted", "hybrid"] = "hosted"
    supported_ratios: list[str] = Field(default_factory=list)
    supported_durations_seconds: list[int] = Field(default_factory=list)
    estimated_cost_cents: int | None = Field(default=None, ge=0)
    estimated_latency_seconds: int | None = Field(default=None, ge=0)
    consent_requirements: list[str] = Field(default_factory=list)
    commercial_use_status: Literal["approved", "restricted", "review_required", "unknown"] = "unknown"
    health: Literal["ready", "degraded", "unavailable", "unverified"] = "unverified"
