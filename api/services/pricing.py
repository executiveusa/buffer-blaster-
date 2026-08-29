"""Commercial package economics and provider-spend guard.

Customer credits are intentionally not provider credits. A package is sellable
only when its provider wallet fits *after* minimum profit, payment fees,
infrastructure, research/LLM overhead, and refund reserve are protected.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)


def _bps_cents(amount_cents: int, bps: int) -> int:
    return math.ceil(max(0, amount_cents) * max(0, bps) / 10_000)


@dataclass(frozen=True, slots=True)
class PackageEconomics:
    offer_id: str
    price_cents: int
    included_ad_credits: int
    provider_budget_cents: int
    minimum_margin_bps: int
    payment_fee_bps: int = 300
    payment_fee_fixed_cents: int = 30
    infrastructure_reserve_bps: int = 500
    research_reserve_bps: int = 300
    refund_reserve_bps: int = 500

    @property
    def payment_fee_reserve_cents(self) -> int:
        return _bps_cents(self.price_cents, self.payment_fee_bps) + max(0, self.payment_fee_fixed_cents)

    @property
    def infrastructure_reserve_cents(self) -> int:
        return _bps_cents(self.price_cents, self.infrastructure_reserve_bps)

    @property
    def research_reserve_cents(self) -> int:
        return _bps_cents(self.price_cents, self.research_reserve_bps)

    @property
    def refund_reserve_cents(self) -> int:
        return _bps_cents(self.price_cents, self.refund_reserve_bps)

    @property
    def non_provider_reserve_cents(self) -> int:
        return (
            self.payment_fee_reserve_cents
            + self.infrastructure_reserve_cents
            + self.research_reserve_cents
            + self.refund_reserve_cents
        )

    @property
    def minimum_margin_cents(self) -> int:
        return _bps_cents(self.price_cents, self.minimum_margin_bps)

    @property
    def max_provider_budget_cents(self) -> int:
        return max(0, self.price_cents - self.minimum_margin_cents - self.non_provider_reserve_cents)

    @property
    def contribution_margin_cents(self) -> int:
        return max(0, self.price_cents - self.provider_budget_cents - self.non_provider_reserve_cents)

    @property
    def contribution_margin_bps(self) -> int:
        if self.price_cents <= 0:
            return 0
        return (self.contribution_margin_cents * 10_000) // self.price_cents

    @property
    def sellable(self) -> bool:
        return (
            self.price_cents > 0
            and self.included_ad_credits > 0
            and 0 <= self.minimum_margin_bps < 10_000
            and self.provider_budget_cents >= 0
            and self.provider_budget_cents <= self.max_provider_budget_cents
            and self.contribution_margin_bps >= self.minimum_margin_bps
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "price_cents": self.price_cents,
            "included_ad_credits": self.included_ad_credits,
            "provider_budget_cents": self.provider_budget_cents,
            "minimum_margin_bps": self.minimum_margin_bps,
            "minimum_margin_cents": self.minimum_margin_cents,
            "payment_fee_reserve_cents": self.payment_fee_reserve_cents,
            "infrastructure_reserve_cents": self.infrastructure_reserve_cents,
            "research_reserve_cents": self.research_reserve_cents,
            "refund_reserve_cents": self.refund_reserve_cents,
            "non_provider_reserve_cents": self.non_provider_reserve_cents,
            "max_provider_budget_cents": self.max_provider_budget_cents,
            "contribution_margin_cents": self.contribution_margin_cents,
            "contribution_margin_bps": self.contribution_margin_bps,
            "sellable": self.sellable,
        }


def _reserve_config() -> dict[str, int]:
    return {
        "payment_fee_bps": _env_int("PAYMENT_FEE_BPS", 300),
        "payment_fee_fixed_cents": _env_int("PAYMENT_FEE_FIXED_CENTS", 30),
        "infrastructure_reserve_bps": _env_int("INFRASTRUCTURE_RESERVE_BPS", 500),
        "research_reserve_bps": _env_int("RESEARCH_RESERVE_BPS", 300),
        "refund_reserve_bps": _env_int("REFUND_RESERVE_BPS", 500),
    }


def default_packages() -> dict[str, PackageEconomics]:
    minimum_margin_bps = _env_int("MIN_CONTRIBUTION_MARGIN_BPS", 6000, minimum=1)
    reserves = _reserve_config()
    values = {
        "trial-7": (
            _env_int("TRIAL_7_PRICE_CENTS", 1900, minimum=1),
            _env_int("TRIAL_7_INCLUDED_AD_CREDITS", 3, minimum=1),
            _env_int("TRIAL_7_PROVIDER_BUDGET_CENTS", 400, minimum=0),
        ),
        "trial-30": (
            _env_int("TRIAL_30_PRICE_CENTS", 4900, minimum=1),
            _env_int("TRIAL_30_INCLUDED_AD_CREDITS", 8, minimum=1),
            _env_int("TRIAL_30_PROVIDER_BUDGET_CENTS", 1100, minimum=0),
        ),
        "starter-monthly": (
            _env_int("STARTER_PRICE_CENTS", 9900, minimum=1),
            _env_int("STARTER_INCLUDED_AD_CREDITS", 20, minimum=1),
            _env_int("STARTER_PROVIDER_BUDGET_CENTS", 2300, minimum=0),
        ),
        "pro-monthly": (
            _env_int("PRO_PRICE_CENTS", 19900, minimum=1),
            _env_int("PRO_INCLUDED_AD_CREDITS", 50, minimum=1),
            _env_int("PRO_PROVIDER_BUDGET_CENTS", 4700, minimum=0),
        ),
    }
    return {
        offer_id: PackageEconomics(
            offer_id=offer_id,
            price_cents=price,
            included_ad_credits=credits,
            provider_budget_cents=budget,
            minimum_margin_bps=minimum_margin_bps,
            **reserves,
        )
        for offer_id, (price, credits, budget) in values.items()
    }


def package_for(offer_id: str) -> PackageEconomics | None:
    return default_packages().get(offer_id)


def authorize_generation(
    *,
    offer_id: str,
    estimated_provider_cost_cents: int,
    remaining_provider_budget_cents: int,
    remaining_ad_credits: int,
) -> dict[str, Any]:
    package = package_for(offer_id)
    if package is None:
        return {"ok": False, "error": "unknown_offer"}
    if not package.sellable:
        return {"ok": False, "error": "unsafe_offer_configuration", "offer": package.to_dict()}
    if estimated_provider_cost_cents < 0:
        return {"ok": False, "error": "invalid_provider_cost"}

    credit_cost_ceiling = _env_int("STANDARD_AD_CREDIT_COST_CENTS", 100, minimum=1)
    ad_credits_required = max(1, math.ceil(estimated_provider_cost_cents / credit_cost_ceiling))

    if estimated_provider_cost_cents > remaining_provider_budget_cents:
        return {
            "ok": False,
            "error": "provider_budget_exceeded",
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "remaining_provider_budget_cents": remaining_provider_budget_cents,
            "ad_credits_required": ad_credits_required,
        }
    if ad_credits_required > remaining_ad_credits:
        return {
            "ok": False,
            "error": "ad_credits_exhausted",
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "ad_credits_required": ad_credits_required,
            "remaining_ad_credits": remaining_ad_credits,
        }

    return {
        "ok": True,
        "offer_id": offer_id,
        "estimated_provider_cost_cents": estimated_provider_cost_cents,
        "ad_credits_required": ad_credits_required,
        "credit_cost_ceiling_cents": credit_cost_ceiling,
        "remaining_provider_budget_after_cents": remaining_provider_budget_cents - estimated_provider_cost_cents,
        "remaining_ad_credits_after": remaining_ad_credits - ad_credits_required,
        "minimum_margin_bps": package.minimum_margin_bps,
        "non_provider_reserve_cents": package.non_provider_reserve_cents,
        "max_provider_budget_cents": package.max_provider_budget_cents,
    }


def public_pricing() -> dict[str, Any]:
    packages = default_packages()
    safe = {key: value.to_dict() for key, value in packages.items()}
    return {
        "ok": all(item["sellable"] for item in safe.values()),
        "packages": safe,
        "standard_ad_credit_cost_ceiling_cents": _env_int("STANDARD_AD_CREDIT_COST_CENTS", 100, minimum=1),
        "reserve_policy": _reserve_config(),
        "rules": {
            "credits_are_cash": False,
            "unused_trial_credits_roll_over": False,
            "provider_spend_cannot_exceed_package_wallet": True,
            "premium_work_can_require_multiple_ad_credits": True,
            "fees_overhead_research_and_refund_reserves_are_protected_before_provider_spend": True,
        },
    }
