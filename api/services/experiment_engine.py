"""Deterministic winner/loser evaluation for proof-first experiments.

This module does not fetch provider data. Platform adapters normalize observations
first; this service evaluates those observations against predeclared thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VariantResult:
    variant_id: str
    role: str
    value: float
    spend_cents: int = 0
    sample_size: int = 0


def evaluate_experiment(
    *,
    primary_kpi: str,
    pass_threshold: float,
    kill_threshold: float | None,
    variants: list[VariantResult],
    higher_is_better: bool = True,
    minimum_sample_size: int = 1,
) -> dict[str, Any]:
    """Return HOLD / PASS / ITERATE / KILL from normalized variant results."""
    if not variants:
        return {"status": "HOLD", "reason": "no_variant_results", "winner_variant_id": None}

    eligible = [v for v in variants if v.sample_size >= minimum_sample_size]
    if not eligible:
        return {
            "status": "HOLD",
            "reason": "minimum_sample_not_reached",
            "winner_variant_id": None,
            "primary_kpi": primary_kpi,
        }

    ranked = sorted(eligible, key=lambda v: v.value, reverse=higher_is_better)
    winner = ranked[0]
    passes = winner.value >= pass_threshold if higher_is_better else winner.value <= pass_threshold

    killed = False
    if kill_threshold is not None:
        killed = winner.value <= kill_threshold if higher_is_better else winner.value >= kill_threshold

    control = next((v for v in eligible if v.role == "control"), None)
    delta = None
    if control is not None:
        delta = winner.value - control.value

    if killed:
        status = "KILL"
        reason = "kill_threshold_crossed"
    elif passes:
        status = "PASS"
        reason = "pass_threshold_crossed"
    else:
        status = "ITERATE"
        reason = "threshold_not_crossed"

    return {
        "status": status,
        "reason": reason,
        "primary_kpi": primary_kpi,
        "winner_variant_id": winner.variant_id if status == "PASS" else None,
        "best_variant_id": winner.variant_id,
        "best_value": winner.value,
        "control_value": control.value if control else None,
        "delta_vs_control": delta,
        "evaluated_variants": len(eligible),
        "total_spend_cents": sum(v.spend_cents for v in eligible),
        "minimum_sample_size": minimum_sample_size,
    }
