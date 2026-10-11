import pytest

from api.routers import mcp as mcp_router


class _Provider:
    configured = True


class _Storage:
    configured = True


class _MediaOps:
    def available(self):
        return True


@pytest.mark.asyncio
async def test_mcp_execute_reserves_exact_executor_estimate(monkeypatch):
    provider = _Provider()
    captured = {}

    async def fake_get_wallet(wallet_id):
        assert wallet_id == "wallet-1"
        return {"id": wallet_id, "state": "active", "offer_id": "offer-1"}

    def fake_estimate(selected_provider, plan, provider_model=None):
        assert selected_provider is provider
        captured["provider_model"] = provider_model
        return {
            "ok": True,
            "estimated_generation_cost_cents": 777,
            "expected_paid_clip_calls": 3,
        }

    async def fake_reserve(wallet_id, *, estimated_provider_cost_cents, idempotency_key):
        captured["reserved"] = {
            "wallet_id": wallet_id,
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "idempotency_key": idempotency_key,
        }
        return {
            "ok": True,
            "wallet_id": wallet_id,
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "remaining_provider_budget_cents": 1000,
            "remaining_ad_credits": 1,
            "idempotency_key": idempotency_key,
        }

    async def fake_execute(brief, **kwargs):
        captured["execute_provider"] = kwargs.get("provider")
        captured["reserved_allowance"] = kwargs.get("reserved_allowance")
        return {"ok": True, "state": "finished"}

    monkeypatch.setattr(mcp_router, "get_wallet", fake_get_wallet)
    monkeypatch.setattr(mcp_router, "get_media_provider", lambda: provider)
    monkeypatch.setattr(mcp_router, "get_asset_storage", lambda: _Storage())
    monkeypatch.setattr(mcp_router, "get_media_ops", lambda: _MediaOps())
    monkeypatch.setattr(mcp_router, "estimate_factory_generation_cost", fake_estimate)
    monkeypatch.setattr(mcp_router, "reserve_generation", fake_reserve)
    monkeypatch.setattr(mcp_router, "execute_ugc_factory_ad", fake_execute)

    result = await mcp_router._execute_factory(
        {
            "product": "Test product",
            "audience": "Test audience",
            "pain": "A recurring problem that needs solving",
            "mechanism": "A repeatable mechanism that solves it",
            "wallet_id": "wallet-1",
            "idempotency_key": "mcp-parity-001",
            "approved": True,
        }
    )

    assert result["ok"] is True
    assert captured["reserved"]["estimated_provider_cost_cents"] == 777
    assert captured["execute_provider"] is provider
    assert captured["reserved_allowance"]["estimated_provider_cost_cents"] == 777


@pytest.mark.asyncio
async def test_mcp_execute_blocks_before_reservation_when_provider_pricing_fails(monkeypatch):
    provider = _Provider()
    reserved = False

    async def fake_get_wallet(_wallet_id):
        return {"id": "wallet-1", "state": "active", "offer_id": "offer-1"}

    async def fake_reserve(*_args, **_kwargs):
        nonlocal reserved
        reserved = True
        return {"ok": True}

    monkeypatch.setattr(mcp_router, "get_wallet", fake_get_wallet)
    monkeypatch.setattr(mcp_router, "get_media_provider", lambda: provider)
    monkeypatch.setattr(mcp_router, "get_asset_storage", lambda: _Storage())
    monkeypatch.setattr(mcp_router, "get_media_ops", lambda: _MediaOps())
    monkeypatch.setattr(
        mcp_router,
        "estimate_factory_generation_cost",
        lambda *_args, **_kwargs: {"ok": False, "error": "model_cost_not_configured"},
    )
    monkeypatch.setattr(mcp_router, "reserve_generation", fake_reserve)

    result = await mcp_router._execute_factory(
        {
            "product": "Test product",
            "audience": "Test audience",
            "pain": "A recurring problem that needs solving",
            "mechanism": "A repeatable mechanism that solves it",
            "wallet_id": "wallet-1",
            "idempotency_key": "mcp-parity-002",
            "approved": True,
        }
    )

    assert result["ok"] is False
    assert result["error"] == "model_cost_not_configured"
    assert result["state"] == "preflight_blocked"
    assert reserved is False
