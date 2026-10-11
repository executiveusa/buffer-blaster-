import pytest

from api.routers import mcp


class FakeProvider:
    configured = True

    def estimate_clip_cost_cents(self, model_name=None):
        assert model_name == "model-x"
        return 100

    def status(self):
        return {"provider": "fake"}


class FakeStorage:
    configured = True


class FakeMediaOps:
    def available(self):
        return True


@pytest.mark.asyncio
async def test_mcp_execute_reservation_matches_executor_pricing(monkeypatch):
    provider = FakeProvider()
    reserved = {}
    executed = {}

    async def fake_wallet(wallet_id):
        assert wallet_id == "wallet-1"
        return {"state": "active", "offer_id": "offer-1"}

    async def fake_reserve(wallet_id, *, estimated_provider_cost_cents, idempotency_key):
        reserved.update(
            wallet_id=wallet_id,
            estimated_provider_cost_cents=estimated_provider_cost_cents,
            idempotency_key=idempotency_key,
        )
        return {
            "ok": True,
            "wallet_id": wallet_id,
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
        }

    async def fake_execute(brief, **kwargs):
        executed["provider"] = kwargs.get("provider")
        executed["allowance"] = kwargs.get("reserved_allowance")
        return {"ok": True}

    monkeypatch.setattr(mcp, "get_wallet", fake_wallet)
    monkeypatch.setattr(mcp, "get_media_provider", lambda: provider)
    monkeypatch.setattr(mcp, "get_asset_storage", lambda: FakeStorage())
    monkeypatch.setattr(mcp, "get_media_ops", lambda: FakeMediaOps())
    monkeypatch.setattr(mcp, "reserve_generation", fake_reserve)
    monkeypatch.setattr(mcp, "execute_ugc_factory_ad", fake_execute)
    monkeypatch.setattr(
        mcp,
        "build_ugc_factory_plan",
        lambda brief: {
            "ok": True,
            "brief": {"provider_model": "model-x"},
            "commercial": {
                "estimated_generation_cost_cents": 999,
                "expected_paid_clip_calls": 3,
                "cost_safety_bps": 12500,
            },
        },
    )

    result = await mcp._execute_factory(
        {
            "product": "Coffee",
            "audience": "Busy parents",
            "pain": "Slow mornings",
            "mechanism": "Fast brew",
            "provider_model": "model-x",
            "wallet_id": "wallet-1",
            "idempotency_key": "idem-12345",
            "approved": True,
        }
    )

    assert result == {"ok": True}
    assert reserved["estimated_provider_cost_cents"] == 375
    assert executed["provider"] is provider
    assert executed["allowance"]["estimated_provider_cost_cents"] == 375
