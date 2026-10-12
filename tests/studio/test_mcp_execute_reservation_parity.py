from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mcp_prices_selected_provider_model_before_wallet_reservation():
    router = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")

    pricing_index = router.index("estimate_factory_generation_cost(provider, plan, provider_model)")
    reserve_index = router.index("reservation = await reserve_generation(")

    assert pricing_index < reserve_index
    assert 'estimated_provider_cost_cents=estimated_cost' in router
    assert "provider=provider" in router


def test_mcp_factory_schema_carries_provider_model_without_vendor_hardcoding():
    router = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")

    assert '"provider_model": {"type": "string"}' in router
    assert "seedance-2.5" not in router.lower()
    assert "kling-3.0" not in router.lower()
    assert "veo-3.1" not in router.lower()


from api.services.ugc_executor import estimate_factory_generation_cost


class _MixedCostProvider:
    configured = True

    def status(self):
        return {"provider": "mixed-cost-test"}

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None):
        return 300 if image_url else 100


class _MissingImageCostProvider:
    configured = True

    def status(self):
        return {"provider": "missing-image-cost-test"}

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None):
        return None if image_url else 100


def test_factory_estimator_prices_one_text_and_two_image_calls():
    result = estimate_factory_generation_cost(
        _MixedCostProvider(),
        {"commercial": {"expected_paid_clip_calls": 3, "cost_safety_bps": 10000}},
    )

    assert result["ok"] is True
    assert result["expected_text_video_calls"] == 1
    assert result["expected_image_video_calls"] == 2
    assert result["estimated_text_clip_cost_cents"] == 100
    assert result["estimated_image_clip_cost_cents"] == 300
    assert result["estimated_generation_cost_cents"] == 700


def test_factory_estimator_blocks_when_image_call_cost_is_unverified():
    result = estimate_factory_generation_cost(
        _MissingImageCostProvider(),
        {"commercial": {"expected_paid_clip_calls": 3, "cost_safety_bps": 10000}},
    )

    assert result == {
        "ok": False,
        "error": "provider_model_not_allowed_or_cost_unverified",
        "model": None,
        "call_kind": "image_to_video",
    }
