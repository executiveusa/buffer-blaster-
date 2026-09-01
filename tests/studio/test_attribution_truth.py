from __future__ import annotations

from api.routers.money_loop import AttributionEvent
from api.routers.shopify_webhooks import _financial_adjustment, _order_ref
from api.services.money_loop import _paid_provider_names
from api.services.performance_ingestion import _provider_refs


def test_orders_paid_is_positive_gross_payment() -> None:
    cents, semantic = _financial_adjustment("orders/paid", {"current_total_price": "49.95"})
    assert cents == 4995
    assert semantic == "gross_payment"


def test_successful_refund_transaction_is_negative_adjustment() -> None:
    cents, semantic = _financial_adjustment(
        "order_transactions/create",
        {"kind": "refund", "status": "success", "amount": "10.25"},
    )
    assert cents == -1025
    assert semantic == "successful_refund"


def test_unsuccessful_or_non_refund_transaction_does_not_change_revenue() -> None:
    assert _financial_adjustment(
        "order_transactions/create",
        {"kind": "refund", "status": "failure", "amount": "10.25"},
    )[0] == 0
    assert _financial_adjustment(
        "order_transactions/create",
        {"kind": "capture", "status": "success", "amount": "49.95"},
    )[0] == 0


def test_refund_and_cancel_webhooks_are_lifecycle_evidence_only() -> None:
    assert _financial_adjustment("refunds/create", {"id": 1}) == (0, "lifecycle_only")
    assert _financial_adjustment("orders/cancelled", {"id": 1}) == (0, "lifecycle_only")


def test_order_reference_is_consistent_across_shopify_topics() -> None:
    assert _order_ref("orders/paid", {"id": 820982911}) == "820982911"
    assert _order_ref("orders/cancelled", {"id": 820982911}) == "820982911"
    assert _order_ref("refunds/create", {"id": 99, "order_id": 820982911}) == "820982911"
    assert _order_ref("order_transactions/create", {"id": 100, "order_id": 820982911}) == "820982911"


def test_manual_attribution_contract_accepts_negative_adjustments() -> None:
    event = AttributionEvent(source="shopify", event_type="order_transactions.create", revenue_cents=-250)
    assert event.revenue_cents == -250


def test_paid_provider_names_detect_conflicting_bindings() -> None:
    refs = {"meta": {"ad_id": "m1"}, "tiktok": {"ad_id": "t1"}}
    assert _paid_provider_names(refs) == {"meta", "tiktok"}
    assert _provider_refs(refs) == []


def test_one_provider_reference_is_evaluable() -> None:
    refs = {"meta": {"campaign_id": "c1", "ad_id": "a1"}}
    assert _provider_refs(refs) == [("meta", refs["meta"])]
