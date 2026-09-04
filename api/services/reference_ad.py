"""Reference-ad intelligence and governed three-variant remix planning.

The service extracts creative mechanics, never source copy or protected brand
identity. Analysis is deterministic and performs no model/provider call. Source,
strategy and variant receipts persist through the canonical media stores.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .media_contracts import UGCPlanDraft
from .media_receipts import (
    _headers,
    _redis_client,
    _supabase_configured,
    _table_url,
    _workspace_id,
    create_ugc_plan,
    get_ugc_plan,
)


_REDIS_REFERENCE_IDEMPOTENCY = "buffer_blaster:reference_ad:idempotency:v1"
_REDIS_REFERENCE_RECEIPT = "buffer_blaster:reference_ad:receipt:v1"
_ALLOWED_RIGHTS = {"owned", "licensed", "authorized_analysis"}
_SHOT_PURPOSES = {"hook", "problem", "demo", "proof", "mechanism", "cta", "transition", "product"}


class ReferenceAdIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_uri: str = Field(min_length=1, max_length=2000)
    source_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-fA-F]{64}$")
    source_owner: str = Field(min_length=1, max_length=255)
    rights_state: Literal["owned", "licensed", "authorized_analysis"]
    mime_type: str = Field(default="video/mp4", min_length=1, max_length=255)
    transcript: str = Field(min_length=1, max_length=40000)
    duration_seconds: int = Field(default=30, ge=1, le=3600)
    shot_notes: list[dict[str, Any]] = Field(default_factory=list)
    client_id: UUID | None = None
    product_source_refs: list[UUID] = Field(min_length=1)
    client_product: str = Field(min_length=1, max_length=255)
    target_audience: str = Field(min_length=1, max_length=500)
    approved_claims: list[str] = Field(default_factory=list, max_length=10)
    protected_brand_terms: list[str] = Field(default_factory=list, max_length=50)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")

    @field_validator("source_sha256")
    @classmethod
    def normalize_hash(cls, value: str) -> str:
        return value.lower()

    @field_validator("protected_brand_terms", "approved_claims")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        return [" ".join(value.split()).strip() for value in values if " ".join(value.split()).strip()]


class ReferenceAdAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hook: str
    problem: str
    promise: str
    proof: str
    cta: str
    pacing: str
    shot_structure: list[dict[str, Any]] = Field(default_factory=list)
    originality_transformations: list[str] = Field(default_factory=list)
    claims_brand_risks: list[str] = Field(default_factory=list)


def _sentences(text: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", text) if segment.strip()]


def analyze_reference_mechanics(intake: ReferenceAdIntake) -> ReferenceAdAnalysis:
    """Classify mechanics without reproducing source language."""
    sentences = _sentences(intake.transcript)
    first = sentences[0].lower() if sentences else ""
    joined = " ".join(sentences).lower()
    last = sentences[-1].lower() if sentences else ""

    negative = ("problem", "tired", "frustrat", "waste", "annoy", "struggl", "kept", "couldn't", "cannot")
    outcome = ("finally", "now", "result", "easier", "faster", "better", "fixed", "changed")
    proof = ("before", "after", "tested", "review", "customer", "people", "%")
    cta = ("shop", "try", "get yours", "learn more", "link", "order", "start")

    hook = "problem_first" if any(token in first for token in negative) else "curiosity_or_claim_first"
    problem_label = "explicit_friction" if any(token in joined for token in negative) else "implicit_need"
    promise_label = "outcome_or_relief" if any(token in joined for token in outcome) else "mechanism_resolution"
    numeric = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", joined))
    if numeric or any(token in joined for token in proof):
        proof_label = "numeric_before_after_or_social_proof"
    elif intake.shot_notes:
        proof_label = "visual_demonstration"
    else:
        proof_label = "not_observed"
    cta_label = "direct_action" if any(token in last for token in cta) else "soft_or_absent"

    sentence_rate = len(sentences) / max(intake.duration_seconds / 60, 1 / 60)
    pacing = "fast" if sentence_rate >= 18 else "medium" if sentence_rate >= 10 else "slow"

    shot_structure: list[dict[str, Any]] = []
    for index, raw in enumerate(intake.shot_notes[:20]):
        purpose = str(raw.get("purpose") or "transition").strip().lower()
        if purpose not in _SHOT_PURPOSES:
            purpose = "transition"
        shot_structure.append({"position": index + 1, "purpose": purpose})

    return ReferenceAdAnalysis(
        hook=hook,
        problem=problem_label,
        promise=promise_label,
        proof=proof_label,
        cta=cta_label,
        pacing=pacing,
        shot_structure=shot_structure,
        originality_transformations=[
            "replace_source_product_identity",
            "rewrite_all_copy_from_client_truth",
            "change_hook_order_across_variants",
            "use_only_mechanics_not_source_phrasing",
        ],
        claims_brand_risks=[
            "source_brand_identity_must_not_be_reused",
            "source_copy_must_not_be_reproduced",
            "client_claims_must_be_preapproved",
        ],
    )


def _request_fingerprint(intake: ReferenceAdIntake) -> str:
    stable = {
        "source_sha256": intake.source_sha256,
        "transcript_sha256": hashlib.sha256(intake.transcript.encode()).hexdigest(),
        "client_id": str(intake.client_id) if intake.client_id else None,
        "product_source_refs": sorted(str(value) for value in intake.product_source_refs),
        "client_product": intake.client_product,
        "target_audience": intake.target_audience,
        "approved_claims": intake.approved_claims,
        "protected_brand_terms": sorted(term.lower() for term in intake.protected_brand_terms),
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _claim_line(intake: ReferenceAdIntake) -> str:
    if intake.approved_claims:
        return intake.approved_claims[0].rstrip(" .") + "."
    return "I would show how it fits the routine before making any outcome claim."


def _assert_original_copy(script: str, intake: ReferenceAdIntake) -> None:
    lower = script.lower()
    product = intake.client_product.lower()
    for term in intake.protected_brand_terms:
        normalized = term.strip().lower()
        if normalized and normalized != product and normalized in lower:
            raise ValueError("protected_reference_brand_term_in_variant")


def _variant_drafts(
    intake: ReferenceAdIntake,
    analysis: ReferenceAdAnalysis,
    strategy_receipt_id: UUID,
    source_id: UUID,
) -> list[tuple[str, UGCPlanDraft]]:
    claim = _claim_line(intake)
    scripts = {
        "control": (
            f"I kept looking for a simpler way to handle the everyday friction. "
            f"I started using {intake.client_product} because it fit the routine. {claim}"
        ),
        "challenger_hook": (
            f"I did not expect {intake.client_product} to be the part I noticed first. "
            f"I would start with the result in context, then show the routine. {claim}"
        ),
        "challenger_proof": (
            f"With {intake.client_product}, I would show the product working before explaining anything. "
            f"Then I would connect it to the everyday problem. {claim}"
        ),
    }
    plans: list[tuple[str, UGCPlanDraft]] = []
    for index, (role, script) in enumerate(scripts.items(), start=1):
        _assert_original_copy(script, intake)
        if role == "control":
            shots = [
                {"shot": 1, "purpose": analysis.hook},
                {"shot": 2, "purpose": "product_mechanism"},
                {"shot": 3, "purpose": analysis.cta},
            ]
        elif role == "challenger_hook":
            shots = [
                {"shot": 1, "purpose": "outcome_first"},
                {"shot": 2, "purpose": analysis.problem},
                {"shot": 3, "purpose": "product_mechanism"},
            ]
        else:
            shots = [
                {"shot": 1, "purpose": analysis.proof},
                {"shot": 2, "purpose": "product_mechanism"},
                {"shot": 3, "purpose": analysis.problem},
            ]
        plans.append(
            (
                role,
                UGCPlanDraft(
                    client_id=intake.client_id,
                    product_source_refs=intake.product_source_refs,
                    strategy_receipt_ref=strategy_receipt_id,
                    script=script,
                    shot_plan=shots,
                    aspect_ratio="9:16",
                    duration_seconds=20,
                    finish_mode="raw_ugc",
                    provider_preference="auto",
                    estimated_cost_ceiling_cents=0,
                    approval_state="draft",
                    idempotency_key=f"{intake.idempotency_key}:variant:{index}",
                    metadata={
                        "reference_source_id": str(source_id),
                        "variant_role": role,
                        "reference_mechanics_only": True,
                        "paid_generation": False,
                    },
                ),
            )
        )
    return plans


def _strategy_record(
    *,
    workspace_id: UUID,
    receipt_id: UUID,
    source_id: UUID,
    intake: ReferenceAdIntake,
    analysis: ReferenceAdAnalysis,
    request_fingerprint: str,
) -> dict[str, Any]:
    return {
        "receipt_id": str(receipt_id),
        "workspace_id": str(workspace_id),
        "client_id": str(intake.client_id) if intake.client_id else None,
        "source_refs": [str(source_id)],
        "source_hashes": [intake.source_sha256],
        "hook_mechanic": analysis.hook,
        "angle": "reference_mechanics_remix",
        "customer_tension": analysis.problem,
        "narrative_structure": "hook_problem_mechanism_proof_cta",
        "pacing": analysis.pacing,
        "creator_archetype": "client_selected_or_product_led",
        "proof_device": analysis.proof,
        "shot_logic": analysis.shot_structure,
        "cta_mechanic": analysis.cta,
        "claims_brand_risks": analysis.claims_brand_risks,
        "originality_transformations": analysis.originality_transformations,
        "recommended_test_variable": "hook_order",
        "model_provenance": {
            "analysis_method": "deterministic-reference-v1",
            "paid_generation": False,
            "source_sha256": intake.source_sha256,
        },
        "idempotency_key": intake.idempotency_key,
        "metadata": {
            "request_fingerprint": request_fingerprint,
            "source_id": str(source_id),
            "variant_plan_ids": [],
            "variant_roles": [],
            "client_product": intake.client_product,
            "target_audience": intake.target_audience,
            "approved_claims": intake.approved_claims,
            "product_source_refs": [str(value) for value in intake.product_source_refs],
            "reference_copy_stored": False,
        },
    }


async def _supabase_existing_strategy(workspace_id: UUID, idempotency_key: str) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            _table_url("strategy_receipts"),
            params={
                "workspace_id": f"eq.{workspace_id}",
                "idempotency_key": f"eq.{idempotency_key}",
                "limit": "1",
            },
            headers=_headers(),
        )
    if not response.is_success:
        return None
    rows = response.json()
    return rows[0] if isinstance(rows, list) and rows else None


async def _supabase_source(workspace_id: UUID, intake: ReferenceAdIntake) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=10) as client:
        existing = await client.get(
            _table_url("creative_sources"),
            params={
                "workspace_id": f"eq.{workspace_id}",
                "kind": "eq.reference_ad",
                "sha256": f"eq.{intake.source_sha256}",
                "limit": "1",
            },
            headers=_headers(),
        )
        if existing.is_success:
            rows = existing.json()
            if isinstance(rows, list) and rows:
                return rows[0]
        source_id = uuid4()
        record = {
            "source_id": str(source_id),
            "workspace_id": str(workspace_id),
            "client_id": str(intake.client_id) if intake.client_id else None,
            "kind": "reference_ad",
            "uri": intake.source_uri,
            "storage_key": None,
            "sha256": intake.source_sha256,
            "mime_type": intake.mime_type,
            "owner": intake.source_owner,
            "rights_state": intake.rights_state,
            "consent_state": "not_applicable",
            "provider_export_allowed": False,
            "metadata": {"analysis_only": True, "reference_copy_stored": False},
        }
        created = await client.post(
            _table_url("creative_sources"),
            json=record,
            headers=_headers(prefer="return=representation"),
        )
    if not created.is_success:
        return None
    rows = created.json()
    return rows[0] if isinstance(rows, list) and rows else record


async def _read_variant_plans(plan_ids: list[str]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for plan_id in plan_ids:
        found = await get_ugc_plan(plan_id)
        if found.get("ok") and found.get("plan"):
            variants.append(found["plan"])
    return variants


async def _create_variant_plans(
    intake: ReferenceAdIntake,
    analysis: ReferenceAdAnalysis,
    receipt_id: UUID,
    source_id: UUID,
) -> tuple[list[str], list[str], list[dict[str, Any]], dict[str, Any] | None]:
    ids: list[str] = []
    roles: list[str] = []
    variants: list[dict[str, Any]] = []
    for role, draft in _variant_drafts(intake, analysis, receipt_id, source_id):
        persisted = await create_ugc_plan(draft)
        if not persisted.get("ok"):
            return ids, roles, variants, persisted
        plan = persisted["plan"]
        ids.append(str(plan["plan_id"]))
        roles.append(role)
        variants.append(plan)
    return ids, roles, variants, None


async def analyze_reference_ad(intake: ReferenceAdIntake) -> dict[str, Any]:
    """Persist source + strategy and create control plus two no-spend challengers."""
    if intake.rights_state not in _ALLOWED_RIGHTS:
        return {"ok": False, "error": "reference_analysis_rights_required", "paid_generation": False}
    try:
        workspace_id = _workspace_id()
    except RuntimeError:
        return {"ok": False, "error": "canonical_workspace_not_configured", "paid_generation": False}

    analysis = analyze_reference_mechanics(intake)
    fingerprint = _request_fingerprint(intake)

    if _supabase_configured():
        existing = await _supabase_existing_strategy(workspace_id, intake.idempotency_key)
        if existing:
            metadata = existing.get("metadata") or {}
            if metadata.get("request_fingerprint") != fingerprint:
                return {"ok": False, "error": "idempotency_conflict", "paid_generation": False}
            plan_ids = [str(value) for value in metadata.get("variant_plan_ids") or []]
            variants = await _read_variant_plans(plan_ids)
            return {
                "ok": len(variants) == 3,
                "strategy": existing,
                "variants": variants,
                "created": False,
                "idempotent_replay": True,
                "paid_generation": False,
                "backend": "supabase",
            }

        source = await _supabase_source(workspace_id, intake)
        if not source:
            return {"ok": False, "error": "reference_source_persistence_failed", "paid_generation": False, "backend": "supabase"}
        source_id = UUID(str(source["source_id"]))
        receipt_id = uuid4()
        strategy = _strategy_record(
            workspace_id=workspace_id,
            receipt_id=receipt_id,
            source_id=source_id,
            intake=intake,
            analysis=analysis,
            request_fingerprint=fingerprint,
        )
        async with httpx.AsyncClient(timeout=10) as client:
            created = await client.post(
                _table_url("strategy_receipts"),
                json=strategy,
                headers=_headers(prefer="return=representation"),
            )
        if not created.is_success:
            if created.status_code == 409:
                replay = await _supabase_existing_strategy(workspace_id, intake.idempotency_key)
                if replay:
                    metadata = replay.get("metadata") or {}
                    if metadata.get("request_fingerprint") != fingerprint:
                        return {"ok": False, "error": "idempotency_conflict", "paid_generation": False}
                    variants = await _read_variant_plans([str(v) for v in metadata.get("variant_plan_ids") or []])
                    return {"ok": len(variants) == 3, "strategy": replay, "variants": variants, "created": False, "idempotent_replay": True, "paid_generation": False, "backend": "supabase"}
            return {"ok": False, "error": "strategy_receipt_persistence_failed", "status": created.status_code, "paid_generation": False, "backend": "supabase"}
        rows = created.json()
        strategy = rows[0] if isinstance(rows, list) and rows else strategy
        ids, roles, variants, failure = await _create_variant_plans(intake, analysis, receipt_id, source_id)
        if failure:
            return {"ok": False, "error": "variant_plan_persistence_failed", "detail": failure, "strategy": strategy, "paid_generation": False, "backend": "supabase"}
        metadata = dict(strategy.get("metadata") or {})
        metadata.update({"variant_plan_ids": ids, "variant_roles": roles})
        async with httpx.AsyncClient(timeout=10) as client:
            patched = await client.patch(
                _table_url("strategy_receipts"),
                params={"receipt_id": f"eq.{receipt_id}", "workspace_id": f"eq.{workspace_id}"},
                json={"metadata": metadata},
                headers=_headers(prefer="return=representation"),
            )
        if not patched.is_success:
            return {"ok": False, "error": "strategy_variant_link_failed", "strategy": strategy, "variants": variants, "paid_generation": False, "backend": "supabase"}
        patched_rows = patched.json()
        final_strategy = patched_rows[0] if isinstance(patched_rows, list) and patched_rows else {**strategy, "metadata": metadata}
        return {"ok": True, "strategy": final_strategy, "variants": variants, "created": True, "idempotent_replay": False, "paid_generation": False, "backend": "supabase"}

    client = await _redis_client()
    if client is None:
        return {"ok": False, "error": "canonical_receipt_store_unavailable", "paid_generation": False, "backend": "unavailable"}
    idem_key = f"{_REDIS_REFERENCE_IDEMPOTENCY}:{workspace_id}:{intake.idempotency_key}"
    try:
        existing_raw = await client.get(idem_key)
        if existing_raw:
            existing = json.loads(existing_raw)
            if existing.get("request_fingerprint") != fingerprint:
                return {"ok": False, "error": "idempotency_conflict", "paid_generation": False, "backend": "redis"}
            return {**existing["response"], "created": False, "idempotent_replay": True}

        source_id = uuid4()
        receipt_id = uuid4()
        strategy = _strategy_record(
            workspace_id=workspace_id,
            receipt_id=receipt_id,
            source_id=source_id,
            intake=intake,
            analysis=analysis,
            request_fingerprint=fingerprint,
        )
        ids, roles, variants, failure = await _create_variant_plans(intake, analysis, receipt_id, source_id)
        if failure:
            return {"ok": False, "error": "variant_plan_persistence_failed", "detail": failure, "paid_generation": False, "backend": "redis"}
        strategy["metadata"]["variant_plan_ids"] = ids
        strategy["metadata"]["variant_roles"] = roles
        response = {"ok": True, "strategy": strategy, "variants": variants, "created": True, "idempotent_replay": False, "paid_generation": False, "backend": "redis"}
        envelope = json.dumps({"request_fingerprint": fingerprint, "response": response}, separators=(",", ":"))
        inserted = await client.set(idem_key, envelope, nx=True)
        if not inserted:
            winner_raw = await client.get(idem_key)
            if winner_raw:
                winner = json.loads(winner_raw)
                if winner.get("request_fingerprint") != fingerprint:
                    return {"ok": False, "error": "idempotency_conflict", "paid_generation": False, "backend": "redis"}
                return {**winner["response"], "created": False, "idempotent_replay": True}
            return {"ok": False, "error": "reference_idempotency_read_failed", "paid_generation": False, "backend": "redis"}
        await client.set(f"{_REDIS_REFERENCE_RECEIPT}:{workspace_id}:{receipt_id}", envelope)
        return response
    finally:
        await client.aclose()


async def get_reference_strategy(receipt_id: str | UUID) -> dict[str, Any]:
    try:
        workspace_id = _workspace_id()
        normalized = UUID(str(receipt_id))
    except (RuntimeError, ValueError):
        return {"ok": False, "error": "invalid_or_unconfigured_reference_receipt", "paid_generation": False}

    if _supabase_configured():
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _table_url("strategy_receipts"),
                params={"receipt_id": f"eq.{normalized}", "workspace_id": f"eq.{workspace_id}", "limit": "1"},
                headers=_headers(),
            )
        if not response.is_success:
            return {"ok": False, "error": "reference_strategy_read_failed", "status": response.status_code, "paid_generation": False}
        rows = response.json()
        strategy = rows[0] if isinstance(rows, list) and rows else None
        if not strategy:
            return {"ok": False, "error": "reference_strategy_not_found", "paid_generation": False, "backend": "supabase"}
        plan_ids = [str(value) for value in (strategy.get("metadata") or {}).get("variant_plan_ids") or []]
        variants = await _read_variant_plans(plan_ids)
        return {"ok": True, "strategy": strategy, "variants": variants, "paid_generation": False, "backend": "supabase"}

    client = await _redis_client()
    if client is None:
        return {"ok": False, "error": "canonical_receipt_store_unavailable", "paid_generation": False, "backend": "unavailable"}
    try:
        raw = await client.get(f"{_REDIS_REFERENCE_RECEIPT}:{workspace_id}:{normalized}")
        if not raw:
            return {"ok": False, "error": "reference_strategy_not_found", "paid_generation": False, "backend": "redis"}
        envelope = json.loads(raw)
        return {**envelope["response"], "created": False, "idempotent_replay": True}
    finally:
        await client.aclose()
