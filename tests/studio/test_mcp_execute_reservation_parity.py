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
