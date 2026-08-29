import os

import pytest

from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan


def _brief(**overrides):
    values = {
        "product": "Cella Coffee",
        "audience": "home baristas who want cafe-quality coffee without a complicated setup",
        "pain": "my morning coffee kept tasting flat even when I bought better beans",
        "mechanism": "the product keeps the brew variables simple and repeatable",
        "offer": "POUR15",
        "platform": "instagram",
    }
    values.update(overrides)
    return UGCFactoryBrief(**values)


def test_factory_returns_two_gated_10_second_clips():
    plan = build_ugc_factory_plan(_brief())

    assert plan["ok"] is True
    assert plan["gate"]["passed"] is True
    assert len(plan["clips"]) == 2
    assert [clip["duration_seconds"] for clip in plan["clips"]] == [10, 10]
    assert plan["clips"][0]["seed_from_previous"] is False
    assert plan["clips"][1]["seed_from_previous"] is True
    assert all(18 <= clip["script_word_count"] <= 32 for clip in plan["clips"])
    assert all("prompt" in clip and "DIALOGUE:" in clip["prompt"] for clip in plan["clips"])


def test_factory_continuity_order_is_explicit_and_safe():
    plan = build_ugc_factory_plan(_brief())
    assert plan["continuity"]["steps"] == [
        "generate_clip_1",
        "trim_clip_1_tail",
        "extract_final_clean_seed_frame",
        "generate_clip_2_from_seed",
        "seam_check",
        "trim_clip_2_tail",
        "stitch",
    ]
    assert plan["continuity"]["seam_threshold_mean_abs_diff"] == pytest.approx(5 / 255)


def test_factory_generated_dialogue_avoids_mechanical_ad_tells():
    plan = build_ugc_factory_plan(_brief())
    dialogue = " ".join(clip["script"] for clip in plan["clips"]).lower()
    banned = ["—", "buy now", "shop now", "link in bio", "don't miss", "miracle", "guaranteed"]
    assert not any(term in dialogue for term in banned)


def test_factory_quote_is_configurable_and_positive_margin(monkeypatch):
    monkeypatch.setenv("UGC_FACTORY_PRICE_CENTS", "9900")
    monkeypatch.setenv("UGC_FACTORY_CLIP_COST_CENTS", "80")
    monkeypatch.setenv("UGC_FACTORY_EXPECTED_CLIPS_PER_AD", "3")
    plan = build_ugc_factory_plan(_brief())
    commercial = plan["commercial"]

    assert commercial["billable_unit"] == "finished_ugc_ad"
    assert commercial["price_cents"] == 9900
    assert commercial["estimated_generation_cost_cents"] == 240
    assert commercial["gross_margin_cents"] == 9660
    assert commercial["gross_margin_pct"] > 90
    assert commercial["charges_customer"] is False


def test_factory_rejects_missing_product_truth():
    with pytest.raises(ValueError):
        build_ugc_factory_plan(_brief(product=""))
