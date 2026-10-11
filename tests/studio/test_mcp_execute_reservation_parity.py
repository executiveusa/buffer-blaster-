import pytest

from api.routers import mcp as mcp_router
from api.services.ugc_executor import estimate_factory_generation_cost
from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan


class FakeProvider:
    configured = True

    def __init__(self, clip_cost=137):
        self.clip_cost = clip_cost

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None):
        return self.clip_cost

    def status(self):
        return {"provider": "fake-gateway"}


class FakeStorage:
    configured = True


class FakeMediaOps:
    def available(self):
        return True


def _args():
    return {
        "product": "Cella Coffee",
        "audience": "home baristas",
        "pain": "coffee tastes inconsistent every morning",
        "mechanism": "repeatable roast and pour variables",
        "offer": "POUR15",
        "platform": "instagram",
        "wallet_id": "wallet-1",
        "idempotency_key": "factory-proof-1",
        "approved": True,
    }


@pytest.mark.asyncio
async def test_mcp_reserves_exact_executor_estimate_and_passes_same_provider(monkeypatch):
    provider = FakeProvider()
    captured = {}

    async def fake_get_wallet(wallet_id):
        assert wallet_id == "wallet-1"
        return {"id": wallet_id, "state": "active", "offer_id": "trial-7"}

    async def fake_reserve(wallet_id, *, estimated_provider_cost_cents, idempotency_key):
        captured["reserved_cost"] = estimated_provider_cost_cents
        captured["idempotency_key"] = idempotency_key
        return {
            "ok": True,
            "wallet_id": wallet_id,
            "estimated_provider_cost_cents": estimated_provider_cost_cents,
            "ad_credits_required": 1,
            "remaining_provider_budget_after_cents": 999,
            "remaining_ad_credits_after": 9,
            "idempotency_key": idempotency_key,
        }

    async def fake_execute(brief, **kwargs):
        captured["provider"] = kwargs.get("provider")
        captured["allowance"] = kwargs.get("reserved_allowance")
        return {"ok": True, "state": "finished"}

    monkeypatch.setattr(mcp_router, "get_wallet", fake_get_wallet)
    monkeypatch.setattr(mcp_router, "get_media_provider", lambda: provider)
    monkeypatch.setattr(mcp_router, "get_asset_storage", lambda: FakeStorage())
    monkeypatch.setattr(mcp_router, "get_media_ops", lambda: FakeMediaOps())
    monkeypatch.setattr(mcp_router, "reserve_generation", fake_reserve)
    monkeypatch.setattr(mcp_router, "execute_ugc_factory_ad", fake_execute)

    result = await mcp_router._execute_factory(_args())

    brief = UGCFactoryBrief(
        product="Cella Coffee",
        audience="home baristas",
        pain="coffee tastes inconsistent every morning",
        mechanism="repeatable roast and pour variables",
        offer="POUR15",
        platform="instagram",
    )
    plan = build_ugc_factory_plan(brief)
    expected = estimate_factory_generation_cost(provider, plan, None)

    assert result["ok"] is True
    assert expected["ok"] is True
    assert captured["reserved_cost"] == expected["estimated_generation_cost_cents"]
    assert captured["allowance"]["estimated_provider_cost_cents"] == expected["estimated_generation_cost_cents"]
    assert captured["provider"] is provider


@pytest.mark.asyncio
async def test_mcp_blocks_before_reservation_when_provider_cost_is_unverified(monkeypatch):
    provider = FakeProvider(clip_cost=None)
    reserve_called = False

    async def fake_get_wallet(wallet_id):
        return {"id": wallet_id, "state": "active", "offer_id": "trial-7"}

    async def fake_reserve(*args, **kwargs):
        nonlocal reserve_called
        reserve_called = True
        return {"ok": True}

    monkeypatch.setattr(mcp_router, "get_wallet", fake_get_wallet)
    monkeypatch.setattr(mcp_router, "get_media_provider", lambda: provider)
    monkeypatch.setattr(mcp_router, "get_asset_storage", lambda: FakeStorage())
    monkeypatch.setattr(mcp_router, "get_media_ops", lambda: FakeMediaOps())
    monkeypatch.setattr(mcp_router, "reserve_generation", fake_reserve)

    result = await mcp_router._execute_factory(_args())

    assert result["ok"] is False
    assert result["error"] == "provider_model_not_allowed_or_cost_unverified"
    assert result["state"] == "preflight_blocked"
    assert reserve_called is False
