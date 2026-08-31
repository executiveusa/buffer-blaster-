from api.services.experiment_engine import VariantResult, evaluate_experiment


def test_passes_best_variant_over_threshold():
    result = evaluate_experiment(
        primary_kpi="roas",
        pass_threshold=2.0,
        kill_threshold=0.5,
        variants=[
            VariantResult("control", "control", 1.2, spend_cents=1000, sample_size=10),
            VariantResult("variant-b", "variant", 2.4, spend_cents=1000, sample_size=10),
        ],
        minimum_sample_size=5,
    )
    assert result["status"] == "PASS"
    assert result["winner_variant_id"] == "variant-b"
    assert result["delta_vs_control"] == 1.2


def test_holds_until_sample_floor():
    result = evaluate_experiment(
        primary_kpi="conversion_rate",
        pass_threshold=0.05,
        kill_threshold=0.01,
        variants=[VariantResult("a", "variant", 0.08, sample_size=2)],
        minimum_sample_size=10,
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "minimum_sample_not_reached"


def test_kills_when_best_result_crosses_kill_floor():
    result = evaluate_experiment(
        primary_kpi="roas",
        pass_threshold=2.0,
        kill_threshold=0.5,
        variants=[VariantResult("a", "variant", 0.3, sample_size=20)],
    )
    assert result["status"] == "KILL"
    assert result["winner_variant_id"] is None
