from api.services.pricing import PackageEconomics, authorize_generation, default_packages


def test_default_paid_trials_keep_positive_margin_after_all_reserves():
    packages = default_packages()
    assert packages["trial-7"].price_cents == 1900
    assert packages["trial-7"].included_ad_credits == 3
    assert packages["trial-7"].provider_budget_cents == 400
    assert packages["trial-30"].price_cents == 4900
    for package in packages.values():
        assert package.non_provider_reserve_cents > 0
        assert package.payment_fee_reserve_cents > 0
        assert package.infrastructure_reserve_cents > 0
        assert package.research_reserve_cents > 0
        assert package.refund_reserve_cents > 0
        assert package.provider_budget_cents <= package.max_provider_budget_cents
        assert package.contribution_margin_bps >= package.minimum_margin_bps


def test_trial_7_house_edge_protects_sixty_percent_margin_after_reserves():
    package = default_packages()["trial-7"]
    assert package.minimum_margin_bps == 6000
    assert package.max_provider_budget_cents == 426
    assert package.provider_budget_cents == 400
    assert package.contribution_margin_bps >= 6000


def test_invalid_package_that_can_go_negative_is_not_sellable():
    package = PackageEconomics(
        offer_id="bad",
        price_cents=1000,
        included_ad_credits=10,
        provider_budget_cents=900,
        minimum_margin_bps=6000,
    )
    assert package.sellable is False


def test_package_can_fail_even_when_provider_only_math_looks_safe():
    package = PackageEconomics(
        offer_id="hidden-overhead",
        price_cents=1000,
        included_ad_credits=4,
        provider_budget_cents=400,
        minimum_margin_bps=6000,
    )
    # 40% provider spend would appear compatible with a 60% margin if fees and
    # overhead were ignored. Protected reserves correctly make it unsellable.
    assert package.max_provider_budget_cents < 400
    assert package.sellable is False


def test_generation_is_denied_when_cost_wallet_cannot_cover_it():
    decision = authorize_generation(
        offer_id="trial-7",
        estimated_provider_cost_cents=500,
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
    )
    assert decision["ok"] is False
    assert decision["error"] == "provider_budget_exceeded"


def test_standard_under_one_dollar_ad_can_consume_one_credit():
    decision = authorize_generation(
        offer_id="trial-7",
        estimated_provider_cost_cents=95,
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
    )
    assert decision["ok"] is True
    assert decision["ad_credits_required"] == 1
    assert decision["remaining_provider_budget_after_cents"] == 305
    assert decision["non_provider_reserve_cents"] > 0
    assert decision["max_provider_budget_cents"] == 426
