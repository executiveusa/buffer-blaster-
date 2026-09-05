"""No-spend Shopify product/context intake for creative planning.

This is not a storefront sync engine. An authenticated operator/agent submits the
minimum product truth needed by Buffer Blaster, which is persisted as a
workspace-scoped creative-job receipt for later planning and attribution work.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .studio_ledger import create_job, get_job


class ShopifyVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    title: str = Field(default="Default", max_length=255)
    price: str | None = Field(default=None, max_length=64)
    sku: str | None = Field(default=None, max_length=128)
    available: bool | None = None


class ShopifyProductContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: UUID
    shop_domain: str = Field(min_length=3, max_length=255)
    product_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=20_000)
    vendor: str | None = Field(default=None, max_length=255)
    product_type: str | None = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list, max_length=100)
    image_urls: list[str] = Field(default_factory=list, max_length=20)
    variants: list[ShopifyVariant] = Field(default_factory=list, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")

    @field_validator("shop_domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        clean = value.strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
        if not clean or "/" in clean or " " in clean:
            raise ValueError("shop_domain must be a hostname")
        return clean

    @field_validator("image_urls")
    @classmethod
    def https_images_only(cls, value: list[str]) -> list[str]:
        for raw in value:
            parsed = urlparse(raw)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError("image_urls must use https")
        return value


def _workspace_id() -> str | None:
    raw = (os.getenv("BUFFER_BLASTER_WORKSPACE_ID") or "").strip()
    if not raw:
        return None
    try:
        return str(UUID(raw))
    except ValueError:
        return None


def build_shopify_context(request: ShopifyProductContextRequest, *, workspace_id: str) -> dict[str, Any]:
    payload = request.model_dump(mode="json")
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt_id = str(uuid5(NAMESPACE_URL, f"buffer-blaster:shopify-context:{workspace_id}:{request.idempotency_key}"))
    available_variants = [row for row in request.variants if row.available is not False]
    price_points = sorted({row.price for row in available_variants if row.price})
    return {
        "receipt_id": receipt_id,
        "workspace_id": workspace_id,
        "client_id": str(request.client_id),
        "shop_domain": request.shop_domain,
        "product_id": request.product_id,
        "product": {
            "title": request.title,
            "description": request.description,
            "vendor": request.vendor,
            "product_type": request.product_type,
            "tags": request.tags,
            "image_urls": request.image_urls,
            "variants": [row.model_dump(mode="json") for row in request.variants],
        },
        "creative_seed": {
            "product_name": request.title,
            "proof_inputs": [item for item in [request.vendor, request.product_type, *request.tags[:8]] if item],
            "image_refs": request.image_urls,
            "available_variant_count": len(available_variants),
            "price_points": price_points,
        },
        "request_fingerprint": fingerprint,
        "paid_generation": False,
    }


async def create_shopify_context(request: ShopifyProductContextRequest) -> dict[str, Any]:
    workspace_id = _workspace_id()
    if not workspace_id:
        return {"ok": False, "error": "canonical_workspace_not_configured", "paid_generation": False}
    context = build_shopify_context(request, workspace_id=workspace_id)
    existing = await get_job(context["receipt_id"])
    if existing:
        if str(existing.get("workspace_id") or "") != workspace_id:
            return {"ok": False, "error": "workspace_scope_mismatch", "paid_generation": False}
        existing_fingerprint = (existing.get("input") or {}).get("request_fingerprint")
        if existing_fingerprint != context["request_fingerprint"]:
            return {"ok": False, "error": "idempotency_conflict", "paid_generation": False}
        return {"ok": True, "created": False, "idempotent_replay": True, "context": existing.get("output") or {}, "job": existing, "paid_generation": False}

    record = await create_job(
        kind="shopify_product_context",
        state="ready",
        job_id=context["receipt_id"],
        input_payload={"request_fingerprint": context["request_fingerprint"], "shop_domain": request.shop_domain, "product_id": request.product_id},
        output_payload=context,
        estimated_provider_cost_cents=0,
    )
    if record.get("ledger_error"):
        return {"ok": False, "error": record["ledger_error"], "paid_generation": False}
    return {"ok": True, "created": True, "context": context, "job": record, "paid_generation": False}


async def get_shopify_context(receipt_id: str) -> dict[str, Any]:
    workspace_id = _workspace_id()
    if not workspace_id:
        return {"ok": False, "error": "canonical_workspace_not_configured"}
    record = await get_job(receipt_id)
    if not record or record.get("kind") != "shopify_product_context":
        return {"ok": False, "error": "shopify_context_not_found"}
    if str(record.get("workspace_id") or "") != workspace_id:
        return {"ok": False, "error": "shopify_context_not_found"}
    return {"ok": True, "context": record.get("output") or {}, "job": record, "paid_generation": False}
