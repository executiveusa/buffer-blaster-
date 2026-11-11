"""The one guarded spend path for the UGC ad factory.

REST (/api/studio/ugc/factory/execute) and MCP (execute_ugc_ad_factory) both
call ``run_factory``. Before this module each surface priced the reservation
its own way, which let MCP reserve one amount while the executor expected
another (wallet debited, then ``invalid_spend_reservation``). One path removes
that whole class of drift.

Order: approval gate -> wallet -> plan gate -> provider pricing -> preflight
-> canonical durability gate (never consume an approval or reserve funds when
the job record cannot persist) -> (agents) consume human approval within its
cost ceiling -> reserve -> execute -> refund in full if no final ad was
stored and returned.
"""
from __future__ import annotations

from typing import Any

from . import usage_ledger
from .agent_access import consume_approval, is_agent, restore_approval
from .studio_ledger import canonical_write_preflight
from .supabase_auth import EXECUTE_ROLES
from .asset_storage import get_asset_storage
from .media_generation import get_media_provider
from .media_ops import get_media_ops
from .ugc_executor import estimate_factory_generation_cost, execute_ugc_factory_ad
from .ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from .usage_wallet import get_wallet, release_reservation, reserve_generation

CONTROL_FIELDS = {"wallet_id", "idempotency_key", "approved", "approval_id", "performance_review"}


def approval_payload(brief_fields: dict[str, Any], wallet_id: str) -> dict[str, Any]:
    """What a human approves: the brief plus the wallet that pays."""
    return {**{k: v for k, v in brief_fields.items() if k not in CONTROL_FIELDS}, "wallet_id": wallet_id}


def estimate_factory(brief_fields: dict[str, Any], *, provider: Any | None = None) -> dict[str, Any]:
    """No-spend estimate using the exact pricing the executor will enforce."""
    brief = UGCFactoryBrief(**{k: v for k, v in brief_fields.items() if k not in CONTROL_FIELDS})
    plan = build_ugc_factory_plan(brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}
    provider = provider or get_media_provider()
    model = str(plan.get("brief", {}).get("provider_model") or "").strip() or None
    casting_ref = str(plan.get("brief", {}).get("casting_reference_url") or "").strip() or None
    # Same full per-clip input contract the executor prices and submits:
    # identity reference list (both shots) + per-clip audio URL slots.
    casting_refs = list(plan.get("brief", {}).get("casting_reference_urls") or [])
    clip_audios = list(plan.get("brief", {}).get("clip_audio_urls") or [])
    pricing = estimate_factory_generation_cost(provider, plan, model, image_url=casting_ref, reference_image_urls=casting_refs, clip_audio_urls=clip_audios)
    if not pricing.get("ok"):
        return {**pricing, "state": "preflight_blocked", "paid_generation": False}
    return {"ok": True, "paid_generation": False, "pricing": pricing,
            "estimated_generation_cost_cents": pricing["estimated_generation_cost_cents"], "plan": plan}


def _max_clip_cost_cents(pricing: dict[str, Any]) -> int:
    """The run's most expensive call shape - the conservative fallback for a
    receipt that reached settlement without its own estimate."""
    costs = (pricing or {}).get("clip_costs_cents") or {}
    values = [int(v) for v in costs.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return max(values) if values else int((pricing or {}).get("estimated_clip_cost_cents") or 0)


def _settlement_cents(clip_receipts: list[dict[str, Any]], fallback_per_clip_cents: int) -> dict[str, int]:
    """Settle every recorded call attempt at its OWN input-shape estimate.

    Three outcome classes, accounted separately:
    - accepted: the call reached the provider -> definite spend.
    - uncertain_after_send: a transport exception at/after send -> the provider
      MAY have received and billed it. Settled conservatively as ESTIMATED
      exposure (never zero), reported separately and never labeled an actual
      charge or a customer bill.
    - rejected: a structured pre-send refusal -> definitely not charged;
      counted for visibility, settled at zero.

    A receipt missing its own estimate falls back to the run's MOST expensive
    call shape - an unknown cost is never settled as zero or as the cheapest
    call. Customers are still refunded in full regardless; this accounting is
    platform-loss visibility, not customer billing.
    """
    definite = 0
    uncertain = 0
    rejected = 0
    for r in clip_receipts:
        if not (r.get("receipt") or r.get("provider_response")):
            continue
        est = r.get("estimated_cents")
        cents = max(0, int(est)) if isinstance(est, (int, float)) and not isinstance(est, bool) else max(0, int(fallback_per_clip_cents))
        outcome = r.get("outcome") or "accepted"
        if outcome == "rejected":
            rejected += 1
        elif outcome == "uncertain_after_send":
            uncertain += cents
        else:
            definite += cents
    return {"definite_cents": definite, "uncertain_estimated_cents": uncertain, "rejected_calls": rejected}


async def run_factory(
    brief_fields: dict[str, Any],
    *,
    wallet_id: str,
    idempotency_key: str,
    approved: bool,
    identity: str,
    approval_id: str | None = None,
    provider: Any | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    agent = is_agent(identity)
    if not agent and approved and role is not None and role not in EXECUTE_ROLES:
        return {"ok": False, "error": "role_denied", "state": "approval_blocked",
                "detail": f"Role '{role}' cannot execute paid runs."}
    if agent and not approval_id:
        return {"ok": False, "error": "human_approval_required", "approval_required": True, "state": "planned",
                "next": "Call request_render_approval, wait for a human decision, then pass approval_id."}
    if not agent and not approved:
        return {"ok": False, "error": "human_approval_required", "approval_required": True, "state": "planned"}
    if len(idempotency_key or "") < 8:
        return {"ok": False, "error": "idempotency_key_required", "state": "spend_blocked"}

    wallet = await get_wallet(wallet_id)
    if not wallet:
        return {"ok": False, "error": "wallet_not_found"}
    if wallet.get("state") != "active":
        return {"ok": False, "error": "wallet_not_active", "wallet_state": wallet.get("state")}

    clean = {k: v for k, v in brief_fields.items() if k not in CONTROL_FIELDS}
    brief = UGCFactoryBrief(**clean)
    plan = build_ugc_factory_plan(brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}
    provider = provider or get_media_provider()
    if not getattr(provider, "configured", False):
        return {"ok": False, "error": "media_provider_not_configured", "state": "preflight_blocked"}
    model = str(plan.get("brief", {}).get("provider_model") or "").strip() or None
    casting_ref = str(plan.get("brief", {}).get("casting_reference_url") or "").strip() or None
    # Same full per-clip input contract the executor prices and submits:
    # identity reference list (both shots) + per-clip audio URL slots.
    casting_refs = list(plan.get("brief", {}).get("casting_reference_urls") or [])
    clip_audios = list(plan.get("brief", {}).get("clip_audio_urls") or [])
    pricing = estimate_factory_generation_cost(provider, plan, model, image_url=casting_ref, reference_image_urls=casting_refs, clip_audio_urls=clip_audios)
    if not pricing.get("ok"):
        return {**pricing, "state": "preflight_blocked"}
    estimated_cost = int(pricing["estimated_generation_cost_cents"])
    if not get_asset_storage().configured:
        return {"ok": False, "error": "asset_storage_not_configured", "state": "preflight_blocked"}
    if not get_media_ops().available():
        return {"ok": False, "error": "ffmpeg_not_available", "state": "preflight_blocked"}

    # Canonical durability gate: never consume a human approval or reserve
    # wallet funds when the job record cannot persist. The executor re-verifies
    # the actual write with a readback before any provider call.
    ledger_preflight = canonical_write_preflight()
    if not ledger_preflight.get("ok"):
        return ledger_preflight

    if agent:
        consumed = await consume_approval(str(approval_id), kind="render", payload=approval_payload(clean, wallet_id), consumer=identity)
        if not consumed.get("ok"):
            return {**consumed, "state": "approval_blocked"}
        if estimated_cost > int(consumed["max_cost_cents"]):
            await restore_approval(str(approval_id))
            return {"ok": False, "error": "estimate_exceeds_approved_cost", "state": "approval_blocked",
                    "estimated_generation_cost_cents": estimated_cost, "approved_max_cost_cents": consumed["max_cost_cents"]}

    # S4: owner-decision caps are enforced BEFORE any reservation with an
    # atomic check+hold, so concurrent runs cannot jointly exceed a cap.
    cap = await usage_ledger.check_and_hold(job_id=idempotency_key, estimated_cents=estimated_cost)
    if not cap.get("ok"):
        if agent:
            await restore_approval(str(approval_id))
        return {**cap, "state": "spend_blocked"}
    hold = cap.get("hold")

    reservation = await reserve_generation(wallet_id, estimated_provider_cost_cents=estimated_cost, idempotency_key=idempotency_key)
    if not reservation.get("ok"):
        await usage_ledger.release_hold(hold)
        if agent:
            await restore_approval(str(approval_id))
        return {**reservation, "state": "spend_blocked"}
    if reservation.get("idempotent_replay"):
        # Same key already reserved (and possibly ran or was refunded). Never
        # execute twice on one reservation.
        await usage_ledger.release_hold(hold)
        return {"ok": False, "error": "idempotency_key_already_used", "state": "spend_blocked", "reservation": reservation}
    reservation["offer_id"] = wallet["offer_id"]

    clip_receipts: list[dict[str, Any]] = []
    settlement = {"definite_cents": 0, "uncertain_estimated_cents": 0, "rejected_calls": 0}
    result: dict[str, Any] | None = None
    error: BaseException | None = None
    try:
        result = await execute_ugc_factory_ad(
            brief, approved=True, offer_id=str(wallet["offer_id"]), reserved_allowance=reservation,
            provider=provider, clip_receipts_sink=clip_receipts,
        )
    except Exception as exc:  # refund still happens; reported as a structured failure
        error = exc
    finally:
        # A stored asset only counts as delivered when the executor could also
        # persist its review state; otherwise the customer gets a full refund
        # and the honest provider exposure is still recorded.
        delivered = bool(result and result.get("final_asset", {}).get("ok") and result.get("customer_deliverable", True))
        settlement = _settlement_cents(clip_receipts, _max_clip_cost_cents(pricing))
        release: dict[str, Any] | None = None
        if not delivered:
            reason = (result or {}).get("state") or (type(error).__name__ if error else "unknown_failure")
            release = await release_reservation(
                wallet_id, idempotency_key=idempotency_key, reason=str(reason),
                provider_cost_incurred_cents=(settlement["definite_cents"] + settlement["uncertain_estimated_cents"]),
            )
    if error is not None:
        result = {"ok": False, "error": "executor_exception", "detail": type(error).__name__, "state": "executor_exception"}
    assert result is not None
    out = {**result, "identity": identity, "refunded": bool(release and release.get("ok")),
           "provider_cost_definite_cents": settlement["definite_cents"],
           "provider_cost_uncertain_estimated_exposure_cents": settlement["uncertain_estimated_cents"],
           "provider_calls_rejected": settlement["rejected_calls"]}
    # S4 ledger: one row per provider clip call, priced at THAT call's own
    # input-shape estimate. actual_cents only when the provider response
    # reported a cost; otherwise NULL (never silent estimates).
    fallback_clip = _max_clip_cost_cents(pricing)
    recorded = 0
    settlement_blocked: list[dict[str, Any]] = []
    for clip in clip_receipts:
        if clip.get("outcome") == "rejected":
            continue  # definitely not charged: visibility lives in provider_calls_rejected
        response = clip.get("provider_response") or {}
        reported_cost = response.get("cost_cents") if isinstance(response, dict) else None
        clip_est = clip.get("estimated_cents")
        caps_provider = getattr(provider, "capabilities", lambda: None)()
        entry = await usage_ledger.record_usage(
            actor=identity, provider=getattr(caps_provider, "provider", "unknown") if caps_provider else "unknown",
            model=model or "default", kind="video",
            job_id=idempotency_key, approval_id=approval_id,
            estimated_cents=int(clip_est) if isinstance(clip_est, (int, float)) and not isinstance(clip_est, bool) else (fallback_clip or None),
            actual_cents=int(reported_cost) if isinstance(reported_cost, int) and reported_cost >= 0 else None,
        )
        if entry.get("ok"):
            recorded += 1
        elif entry.get("error") == "cost_unknown":
            out["usage_ledger_errors"] = out.get("usage_ledger_errors", []) + [entry]
        else:
            # Durable-write failure (ledger_write_failed / store unavailable /
            # workspace missing): the exposure must NOT go unrecorded while the
            # cap hold is freed.
            settlement_blocked.append(entry)
    if settlement_blocked:
        # Fail closed: the cap hold stays PENDING (reconcilable by the existing
        # hold/release machinery) until the usage rows are canonical and
        # durable. This blocker is reported separately from the cost_unknown
        # backlog (usage_ledger_errors): unknown-cost rows are content
        # rejections, these are durability failures.
        out["usage_settlement_blocked"] = {
            "error": "usage_ledger_not_durable",
            "unrecorded_calls": len(settlement_blocked),
            "hold_id": (hold or {}).get("hold_id"),
            "hold_released": False,
            "errors": settlement_blocked,
        }
    else:
        # Settle the cap hold: recorded rows now count as spent; release the rest.
        await usage_ledger.release_hold(hold)
    if recorded:
        out["usage_events_recorded"] = recorded
    if release is not None:
        out["release"] = release
    if approval_id:
        out["approval_id"] = approval_id
    return out


async def request_render_approval(brief_fields: dict[str, Any], *, wallet_id: str, requested_by: str) -> dict[str, Any]:
    """Create a pending render approval priced by the server, never the caller."""
    from .agent_access import request_approval

    if not wallet_id:
        return {"ok": False, "error": "wallet_id_required"}
    estimate = estimate_factory(brief_fields)
    if not estimate.get("ok"):
        return estimate
    cost = int(estimate["estimated_generation_cost_cents"])
    clean = {k: v for k, v in brief_fields.items() if k not in CONTROL_FIELDS}
    summary = f"Render 2-clip UGC ad for {clean.get('product', '?')} to {clean.get('audience', '?')}; est {cost} cents from wallet {wallet_id}"
    created = await request_approval(kind="render", payload=approval_payload(clean, wallet_id), requested_by=requested_by,
                                     max_cost_cents=cost, summary=summary)
    return {**created, "estimated_generation_cost_cents": cost} if created.get("ok") else created
