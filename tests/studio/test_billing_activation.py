import pytest

from api.services.billing import activate_checkout_session


@pytest.mark.asyncio
async def test_activation_rejects_unpaid_checkout(monkeypatch):
    async def fake_fetch(_session_id):
        return {
            "ok": True,
            "session": {
                "id": "cs_test_unpaid",
                "payment_status": "unpaid",
                "metadata": {"offer": "trial-7"},
                "amount_total": 1900,
                "currency": "usd",
            },
        }

    monkeypatch.setattr("api.services.billing.fetch_checkout_session", fake_fetch)
    result = await activate_checkout_session("cs_test_unpaid")
    assert result["ok"] is False
    assert result["error"] == "checkout_not_paid"


@pytest.mark.asyncio
async def test_activation_verifies_offer_amount_before_wallet(monkeypatch):
    async def fake_fetch(_session_id):
        return {
            "ok": True,
            "session": {
                "id": "cs_test_bad_amount",
                "payment_status": "paid",
                "metadata": {"offer": "trial-7"},
                "amount_total": 100,
                "currency": "usd",
            },
        }

    monkeypatch.setattr("api.services.billing.fetch_checkout_session", fake_fetch)
    result = await activate_checkout_session("cs_test_bad_amount")
    assert result["ok"] is False
    assert result["error"] == "checkout_amount_mismatch"


@pytest.mark.asyncio
async def test_activation_creates_server_wallet_only_after_paid_verified_checkout(monkeypatch):
    async def fake_fetch(_session_id):
        return {
            "ok": True,
            "session": {
                "id": "cs_test_paid",
                "payment_status": "paid",
                "metadata": {"offer": "trial-7"},
                "amount_total": 1900,
                "currency": "usd",
                "customer": "cus_123",
            },
        }

    created = {}

    async def fake_create_wallet(**kwargs):
        created.update(kwargs)
        return {"ok": True, "wallet": {"id": "wallet-1", "offer_id": kwargs["offer_id"]}}

    monkeypatch.setattr("api.services.billing.fetch_checkout_session", fake_fetch)
    monkeypatch.setattr("api.services.billing.create_wallet", fake_create_wallet)

    result = await activate_checkout_session("cs_test_paid")
    assert result["ok"] is True
    assert result["wallet"]["id"] == "wallet-1"
    assert created == {
        "offer_id": "trial-7",
        "customer_ref": "cus_123",
        "checkout_session_id": "cs_test_paid",
    }
