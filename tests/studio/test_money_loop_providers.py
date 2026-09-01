from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from api.routers.shopify_webhooks import _attribution_ids, _event_id, verify_shopify_hmac
from api.services.money_loop import _scoped_params as money_loop_scoped_params
from api.services.performance_ingestion import (
    _performance_params,
    _scoped_params as ingestion_scoped_params,
)
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


def test_performance_reads_are_scoped_to_experiment_variant_and_creative() -> None:
    assert _performance_params(
        experiment_id="exp-1",
        variant_id="var-1",
        content_item_id="creative-1",
    ) == {
        "content_item_id": "eq.creative-1",
        "metadata->>experiment_id": "eq.exp-1",
        "metadata->>variant_id": "eq.var-1",
        "order": "observed_at.desc",
        "limit": "100",
    }


def test_paid_media_providers_report_full_delivery_implementation() -> None:
    for provider in (MetaAdsProvider(), TikTokAdsProvider()):
        status = provider.status()
        assert status["launch_scope"] == "full_delivery_hierarchy"
        assert status["delivery_ready"] is True
        assert status["live_verified"] is False


@pytest.mark.asyncio
async def test_meta_launch_requires_human_approval() -> None:
    result = await MetaAdsProvider().create_experiment({"campaign": {"name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_tiktok_launch_requires_human_approval() -> None:
    result = await TikTokAdsProvider().create_experiment({"campaign": {"campaign_name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_meta_activation_requires_human_approval() -> None:
    result = await MetaAdsProvider().activate_experiment(
        {"campaign_id": "c", "adset_id": "s", "ad_id": "a"}, approved=False
    )
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_tiktok_activation_requires_human_approval() -> None:
    result = await TikTokAdsProvider().activate_experiment(
        {"campaign_id": "c", "adgroup_id": "g", "ad_id": "a"}, approved=False
    )
    assert result == {"ok": False, "error": "human_approval_required"}


class FakeAsyncClient:
    instances: list["FakeAsyncClient"] = []
    responses: list[httpx.Response] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._responses = list(type(self).responses)
        type(self).instances.append(self)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    def _next(self) -> httpx.Response:
        assert self._responses, "fake response queue exhausted"
        return self._responses.pop(0)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append(("POST", url, kwargs))
        return self._next()

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append(("GET", url, kwargs))
        return self._next()


def response(status: int, payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "https://example.test"))


@pytest.mark.asyncio
async def test_meta_creates_complete_paused_hierarchy(monkeypatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("META_AD_ACCOUNT_ID", "act_123")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v-test")
    FakeAsyncClient.instances.clear()
    FakeAsyncClient.responses = [
        response(200, {"id": "campaign-1"}),
        response(200, {"id": "adset-1"}),
        response(200, {"id": "creative-1"}),
        response(200, {"id": "ad-1"}),
        response(200, {"id": "ad-1", "status": "PAUSED"}),
    ]
    monkeypatch.setattr("api.services.providers.meta_ads.httpx.AsyncClient", FakeAsyncClient)

    result = await MetaAdsProvider().create_experiment(
        {
            "campaign": {"name": "proof", "objective": "OUTCOME_SALES"},
            "ad_set": {"name": "proof-set", "daily_budget": "1000"},
            "creative": {"name": "proof-creative", "object_story_spec": {"page_id": "p"}},
            "ad": {"name": "proof-ad"},
        },
        approved=True,
    )

    assert result["ok"] is True
    assert result["external_ref"] == {
        "campaign_id": "campaign-1",
        "adset_id": "adset-1",
        "creative_id": "creative-1",
        "ad_id": "ad-1",
    }
    calls = FakeAsyncClient.instances[-1].calls
    assert calls[0][2]["data"]["status"] == "PAUSED"
    assert calls[1][2]["data"]["campaign_id"] == "campaign-1"
    assert calls[1][2]["data"]["status"] == "PAUSED"
    assert json.loads(calls[2][2]["data"]["object_story_spec"]) == {"page_id": "p"}
    assert calls[3][2]["data"]["adset_id"] == "adset-1"
    assert json.loads(calls[3][2]["data"]["creative"]) == {"creative_id": "creative-1"}
    assert calls[3][2]["data"]["status"] == "PAUSED"


@pytest.mark.asyncio
async def test_tiktok_creates_complete_disabled_hierarchy(monkeypatch) -> None:
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("TIKTOK_ADVERTISER_ID", "advertiser-1")
    monkeypatch.setenv("TIKTOK_API_BASE_URL", "https://business-api.tiktok.com/open_api/v1.3")
    FakeAsyncClient.instances.clear()
    FakeAsyncClient.responses = [
        response(200, {"code": 0, "data": {"campaign_id": "campaign-1"}}),
        response(200, {"code": 0, "data": {}}),
        response(200, {"code": 0, "data": {"adgroup_id": "adgroup-1"}}),
        response(200, {"code": 0, "data": {"ad_id": "ad-1"}}),
        response(200, {"code": 0, "data": {"list": [{"ad_id": "ad-1"}]}}),
    ]
    monkeypatch.setattr("api.services.providers.tiktok_ads.httpx.AsyncClient", FakeAsyncClient)

    result = await TikTokAdsProvider().create_experiment(
        {
            "campaign": {"campaign_name": "proof", "objective_type": "TRAFFIC"},
            "ad_group": {"adgroup_name": "proof-group", "budget": 20},
            "ad": {"ad_name": "proof-ad", "creatives": [{"ad_text": "proof"}]},
        },
        approved=True,
    )

    assert result["ok"] is True
    assert result["external_ref"] == {
        "campaign_id": "campaign-1",
        "adgroup_id": "adgroup-1",
        "ad_id": "ad-1",
    }
    calls = FakeAsyncClient.instances[-1].calls
    assert calls[1][1].endswith("/campaign/status/update/")
    assert calls[1][2]["json"]["operation_status"] == "DISABLE"
    assert calls[2][2]["json"]["campaign_id"] == "campaign-1"
    assert calls[2][2]["json"]["operation_status"] == "DISABLE"
    assert calls[3][2]["json"]["adgroup_id"] == "adgroup-1"
    assert calls[3][2]["json"]["operation_status"] == "DISABLE"
