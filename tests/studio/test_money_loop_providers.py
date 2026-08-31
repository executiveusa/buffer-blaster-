from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from api.routers.shopify_webhooks import _attribution_ids, verify_shopify_hmac
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


@pytest.mark.asyncio
async def test_meta_launch_requires_human_approval() -> None:
    result = await MetaAdsProvider().create_experiment({"campaign": {"name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}


@pytest.mark.asyncio
async def test_tiktok_launch_requires_human_approval() -> None:
    result = await TikTokAdsProvider().create_experiment({"campaign": {"campaign_name": "test"}}, approved=False)
    assert result == {"ok": False, "error": "human_approval_required"}
