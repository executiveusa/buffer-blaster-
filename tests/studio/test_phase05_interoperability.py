from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.services import shopify_context
from api.services.publishing import DisabledPublishingProvider, PublishRequest
from api.services.shopify_context import ShopifyProductContextRequest, build_shopify_context

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_A = "11111111-1111-4111-8111-111111111111"
WORKSPACE_B = "22222222-2222-4222-8222-222222222222"


def _request(**changes):
    payload = {
        "client_id": str(uuid4()),
        "shop_domain": "store.example.com",
        "product_id": "gid://shopify/Product/42",
        "title": "Proof Hoodie",
        "description": "Heavyweight hoodie with reinforced seams.",
        "vendor": "Example",
        "product_type": "Hoodie",
        "tags": ["heavyweight", "streetwear"],
        "image_urls": ["https://cdn.example.com/hoodie.jpg"],
        "variants": [{"id": "v1", "title": "Black / L", "price": "89.00", "available": True}],
        "idempotency_key": "phase05-shopify-001",
    }
    payload.update(changes)
    return ShopifyProductContextRequest(**payload)


def test_shopify_context_normalizes_domain_and_rejects_non_https_images():
    request = _request(shop_domain="HTTPS://Store.Example.com/")
    assert request.shop_domain == "store.example.com"
    with pytest.raises(ValidationError):
        _request(image_urls=["http://cdn.example.com/hoodie.jpg"])


def test_context_receipt_is_workspace_scoped_and_deterministic():
    request = _request()
    a = build_shopify_context(request, workspace_id=WORKSPACE_A)
    a2 = build_shopify_context(request, workspace_id=WORKSPACE_A)
    b = build_shopify_context(request, workspace_id=WORKSPACE_B)
    assert a == a2
    assert a["receipt_id"] != b["receipt_id"]
    assert a["workspace_id"] == WORKSPACE_A
    assert a["paid_generation"] is False
    assert a["creative_seed"]["product_name"] == "Proof Hoodie"


@pytest.mark.asyncio
async def test_create_replay_conflict_and_cross_workspace_read_fail_closed(monkeypatch):
    stored = {}
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_A)

    async def fake_get(job_id):
        return stored.get(job_id)

    async def fake_create(**kwargs):
        record = {
            "id": kwargs["job_id"],
            "workspace_id": WORKSPACE_A,
            "kind": kwargs["kind"],
            "state": kwargs["state"],
            "input": kwargs["input_payload"],
            "output": kwargs["output_payload"],
        }
        stored[record["id"]] = record
        return record

    monkeypatch.setattr(shopify_context, "get_job", fake_get)
    monkeypatch.setattr(shopify_context, "create_job", fake_create)

    first = await shopify_context.create_shopify_context(_request())
    replay = await shopify_context.create_shopify_context(_request())
    conflict = await shopify_context.create_shopify_context(_request(title="Different product truth"))
    assert first["ok"] is True and first["created"] is True
    assert replay["ok"] is True and replay["idempotent_replay"] is True
    assert conflict == {"ok": False, "error": "idempotency_conflict", "paid_generation": False}

    receipt_id = first["context"]["receipt_id"]
    monkeypatch.setenv("BUFFER_BLASTER_WORKSPACE_ID", WORKSPACE_B)
    denied = await shopify_context.get_shopify_context(receipt_id)
    assert denied == {"ok": False, "error": "shopify_context_not_found"}


@pytest.mark.asyncio
async def test_disabled_publisher_and_unapproved_publish_fail_closed():
    provider = DisabledPublishingProvider()
    accounts = await provider.list_accounts()
    assert accounts["ok"] is False
    request = PublishRequest(content="proof", platforms=[], scheduled_at="", approved=False)
    result = await provider.schedule(request)
    assert result == {"ok": False, "error": "human_approval_required"}


def test_rest_mcp_cli_high_value_interface_parity():
    rest = (ROOT / "api/routers/shopify_context.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    cli = (ROOT / "cli/blaster.py").read_text(encoding="utf-8")
    webhook = (ROOT / "api/routers/shopify_webhooks.py").read_text(encoding="utf-8")
    publishing = (ROOT / "api/services/publishing.py").read_text(encoding="utf-8")

    assert '@router.post("/context")' in rest
    assert '@router.get("/context/{receipt_id}")' in rest
    assert '"name": "create_shopify_product_context"' in mcp
    assert '"name": "get_shopify_product_context"' in mcp
    assert '"name": "sync_experiment_evidence"' in mcp
    assert "shopify-context" in cli and "shopify-context-get" in cli
    assert "experiment-sync" in cli

    assert "verify_shopify_hmac" in webhook
    assert "BUFFER_API_KEY" in publishing
    assert "human_approval_required" in publishing
    assert "reserve_generation" not in (ROOT / "api/services/shopify_context.py").read_text(encoding="utf-8")


def test_consequential_mcp_and_rest_surfaces_are_authenticated():
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    studio = (ROOT / "api/routers/studio.py").read_text(encoding="utf-8")
    money = (ROOT / "api/routers/money_loop.py").read_text(encoding="utf-8")
    assert "verify_operator(request)" in mcp
    assert "Depends(verify_operator)" in studio
    assert "Depends(verify_operator)" in money
