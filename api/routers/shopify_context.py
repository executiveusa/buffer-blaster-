"""Authenticated no-spend Shopify product-context intake routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services.integration_auth import verify_operator
from ..services.shopify_context import ShopifyProductContextRequest, create_shopify_context, get_shopify_context

router = APIRouter(prefix="/api/studio/shopify", tags=["shopify-context"])


@router.post("/context")
async def create_context(request: ShopifyProductContextRequest, _=Depends(verify_operator)) -> dict:
    return await create_shopify_context(request)


@router.get("/context/{receipt_id}")
async def get_context(receipt_id: str, _=Depends(verify_operator)) -> dict:
    return await get_shopify_context(receipt_id)
