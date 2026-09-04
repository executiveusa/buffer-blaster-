"""Server-owned UGC/avatar provider registry and no-spend route planner."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Literal
from uuid import UUID, uuid5, NAMESPACE_URL

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .media_contracts import ProviderCapabilities
from .media_generation import get_media_provider
from .usage_wallet import get_wallet


CapabilityName = Literal[
    "talking_creator",
    "image_to_video",
    "text_to_video",
    "lip_sync",
    "audio_driven",
    "body_motion",
]
RoutePreference = Literal["auto", "fast", "premium", "sovereign"]


class ProviderRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capabilities: ProviderCapabilities
    enabled: bool = True
    quality_rank: int = Field(default=50, ge=0, le=100)
    cost_class: Literal["free_local", "low", "standard", "premium", "unknown"] = "unknown"
    provenance: str = "runtime_config"


class ProviderRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: CapabilityName
    plan_id: UUID | None = None
    reference_count: int = Field(default=0, ge=0, le=16)
    aspect_ratio: Literal["9:16", "16:9", "1:1", "4:5"] = "9:16"
    duration_seconds: int = Field(default=10, ge=1, le=300)
    preference: RoutePreference = "auto"
    wallet_id: str | None = Field(default=None, max_length=255)
    requested_cost_ceiling_cents: int | None = Field(default=None, ge=0)
    requires_person_identity: bool = False
    consent_refs: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _fal_entry() -> ProviderRegistryEntry:
    provider = get_media_provider()
    caps = provider.capabilities()
    if caps.commercial_use_status == "review_required" and _truthy("FAL_COMMERCIAL_USE_APPROVED"):
        caps = caps.model_copy(update={"commercial_use_status": "approved"})
    try:
        quality = max(0, min(100, int(os.getenv("FAL_QUALITY_RANK", "60"))))
    except ValueError:
        quality = 60
    return ProviderRegistryEntry(
        capabilities=caps,
        enabled=provider.configured,
        quality_rank=quality,
        cost_class=os.getenv("FAL_COST_CLASS", "standard") if os.getenv("FAL_COST_CLASS", "standard") in {"free_local", "low", "standard", "premium", "unknown"} else "unknown",
        provenance="fal_runtime_configuration",
    )


def _configured_entries() -> list[ProviderRegistryEntry]:
    raw = (os.getenv("UGC_PROVIDER_REGISTRY_JSON") or "").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    entries: list[ProviderRegistryEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            entries.append(ProviderRegistryEntry.model_validate(item))
        except ValidationError:
            continue
    return entries


def provider_registry() -> list[ProviderRegistryEntry]:
    """Return enabled/disabled provider metadata with no secrets or model IDs."""
    by_name: dict[str, ProviderRegistryEntry] = {"fal": _fal_entry()}
    for entry in _configured_entries():
        by_name[entry.capabilities.provider] = entry
    return list(by_name.values())


def _supports(entry: ProviderRegistryEntry, request: ProviderRouteRequest) -> bool:
    cap = entry.capabilities
    if not entry.enabled or cap.health != "ready":
        return False
    if cap.commercial_use_status in {"restricted", "unknown"}:
        return False
    if request.preference == "sovereign" and cap.deployment not in {"local", "hybrid"}:
        return False
    if request.reference_count > cap.max_reference_images:
        return False
    if cap.supported_ratios and request.aspect_ratio not in cap.supported_ratios:
        return False
    if cap.supported_durations_seconds and request.duration_seconds not in cap.supported_durations_seconds:
        return False
    if request.capability == "talking_creator":
        return cap.image_to_video and (cap.lip_sync or cap.audio_driven)
    if request.capability == "image_to_video":
        return cap.image_to_video
    if request.capability == "text_to_video":
        return cap.text_to_video
    if request.capability == "lip_sync":
        return cap.lip_sync
    if request.capability == "audio_driven":
        return cap.audio_driven
    if request.capability == "body_motion":
        return cap.body_motion
    return False


def _server_ceiling() -> int:
    try:
        return max(0, int(os.getenv("UGC_ROUTE_MAX_COST_CENTS", "200")))
    except ValueError:
        return 200


def _fingerprint(request: ProviderRouteRequest, effective_ceiling: int) -> str:
    payload = request.model_dump(mode="json", exclude={"wallet_id"})
    payload["effective_cost_ceiling_cents"] = effective_ceiling
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _score(entry: ProviderRegistryEntry, preference: RoutePreference) -> tuple[int, int, int, str]:
    cap = entry.capabilities
    cost = cap.estimated_cost_cents if cap.estimated_cost_cents is not None else 10**9
    latency = cap.estimated_latency_seconds if cap.estimated_latency_seconds is not None else 10**9
    if preference == "premium":
        return (-entry.quality_rank, cost, latency, cap.provider)
    if preference == "fast":
        return (latency, cost, -entry.quality_rank, cap.provider)
    if preference == "sovereign":
        local_rank = 0 if cap.deployment == "local" else 1
        return (local_rank, cost, latency, cap.provider)
    return (cost, latency, -entry.quality_rank, cap.provider)


async def plan_provider_route(request: ProviderRouteRequest) -> dict[str, Any]:
    """Choose a provider without spending. A client request can only reduce ceilings."""
    if request.requires_person_identity and not request.consent_refs:
        return {"ok": False, "error": "identity_consent_required", "paid_generation": False}

    server_ceiling = _server_ceiling()
    wallet_budget: int | None = None
    if request.wallet_id:
        wallet = await get_wallet(request.wallet_id)
        if not wallet:
            return {"ok": False, "error": "wallet_not_found", "paid_generation": False}
        if wallet.get("state") != "active":
            return {"ok": False, "error": "wallet_not_active", "wallet_state": wallet.get("state"), "paid_generation": False}
        wallet_budget = max(0, int(wallet.get("remaining_provider_budget_cents") or 0))

    ceilings = [server_ceiling]
    if wallet_budget is not None:
        ceilings.append(wallet_budget)
    if request.requested_cost_ceiling_cents is not None:
        ceilings.append(request.requested_cost_ceiling_cents)
    effective_ceiling = min(ceilings)

    eligible: list[ProviderRegistryEntry] = []
    rejected: list[dict[str, Any]] = []
    for entry in provider_registry():
        cap = entry.capabilities
        if not _supports(entry, request):
            rejected.append({"provider": cap.provider, "reason": "capability_or_policy_mismatch"})
            continue
        estimate = cap.estimated_cost_cents
        if estimate is None:
            rejected.append({"provider": cap.provider, "reason": "cost_unverified"})
            continue
        if estimate > effective_ceiling:
            rejected.append({"provider": cap.provider, "reason": "insufficient_budget", "estimated_cost_cents": estimate})
            continue
        eligible.append(entry)

    fingerprint = _fingerprint(request, effective_ceiling)
    route_id = str(uuid5(NAMESPACE_URL, f"buffer-blaster:{request.idempotency_key}:{fingerprint}"))
    if not eligible:
        return {
            "ok": False,
            "error": "no_eligible_provider",
            "route_id": route_id,
            "request_fingerprint": fingerprint,
            "effective_cost_ceiling_cents": effective_ceiling,
            "rejected": rejected,
            "paid_generation": False,
        }

    chosen = sorted(eligible, key=lambda item: _score(item, request.preference))[0]
    cap = chosen.capabilities
    return {
        "ok": True,
        "route_id": route_id,
        "request_fingerprint": fingerprint,
        "idempotent": True,
        "capability": request.capability,
        "preference": request.preference,
        "provider": cap.provider,
        "deployment": cap.deployment,
        "estimated_cost_cents": cap.estimated_cost_cents,
        "effective_cost_ceiling_cents": effective_ceiling,
        "estimated_latency_seconds": cap.estimated_latency_seconds,
        "quality_rank": chosen.quality_rank,
        "commercial_use_status": cap.commercial_use_status,
        "consent_requirements": cap.consent_requirements,
        "reference_count": request.reference_count,
        "paid_generation": False,
        "spend_reserved": False,
        "approval_required_before_execution": True,
        "wallet_authority_unchanged": True,
        "rejected": rejected,
    }
