from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from api.routers.shopify_webhooks import _attribution_ids, _event_id, verify_shopify_hmac
from api.services.money_loop import _scoped_params as money_loop_scoped_params
from api.services.performance_ingestion import _scoped_params as ingestion_scoped_params
from api.services.providers.meta_ads import MetaAdsProvider
from api.services.providers.tiktok_ads import TikTokAdsProvider


def test_shopify_hmac_verification_uses_raw_body() -> None:
    body = b'{"id":123,"total_price":"49.00"}'
    secret = "test-secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_shopify_hmac(body, signature, secret) is True
    assert verify_shopify_hmac(body + b" ", signature, secret) is False


def test_shopify_attribution_extracts_tracking_query() -> None:
    experiment_id, variant_id = _attribution_ids({
        "landing_site": "/products/widget?utm_source=meta&bb_exp=exp-123&bb_var=var-b"
    })
    assert experiment_id == "exp-123"
    assert variant_id == "var-b"


def test_shopify_attribution_accepts_order_attributes() -> None:
    experiment_id, variant_id = _attribution_ids({
        "note_attributes": [
            {"name": "bb_exp", "value": "exp-9"},
            {"name": "bb_var", "value": "var-2"},
        ]
    })
    assert experiment_id == "exp-9"
    assert variant_id == "var-2"


def test_shopify_event_id_prefers_event_then_webhook_then_payload() -> None:
    assert _event_id("event-1", "webhook-1", {"id": 123}) == "event-1"
    assert _event_id("", "webhook-1", {"id": 123}) == "webhook-1"
    assert _event_id("", "", {"id": 123}) == "123"
    assert _event_id("", "", {}) == ""


def test_money_loop_queries_are_scoped_to_configured_workspace(monkeypatch) -> None:
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", "00000000-0000-0000-0000-000000000001")
    expected = "eq.00000000-0000-0000-0000-000000000001"
    assert money_loop_scoped_params({"id": "eq.exp-1"}) == {
        "workspace_id": expected,
        "id": "eq.exp-1",
    }
    assert ingestion_scoped_params({"content_item_id": "eq.asset-1"}) == {
        "workspace_id": expected,
        "content_item_id": "eq.asset-1",
    }


def test_paid_media_providers_report_campaign_only_launch_scope() -> None:
    for provider in (MetaAdsProvider(), TikTokAdsProvider()):
        status = provider.status()
        assert status["launch_scope"] == "campaign_container_only"
        assert status["delivery_ready"] is False


@pytest.mark.asyncio
async def test_meta_launch_requires_human_approval() -> None:
    result = await MetaAdsProvider().create_experiment({"campaign": {"name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_tiktok_launch_requires_human_approval() -> None:
    result = await TikTokAdsProvider().create_experiment({"campaign": {"campaign_name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}
