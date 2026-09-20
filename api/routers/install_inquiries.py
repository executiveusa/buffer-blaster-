"""Public install-interest intake. No operator secret is accepted or returned."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..services.install_inquiries import create_install_inquiry

router = APIRouter(prefix="/api/install-inquiries", tags=["install-inquiries"])


class InquiryPayload(BaseModel):
    email: str
    bot_field: str = ""


@router.post("")
async def create(payload: InquiryPayload, request: Request) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "")
    source = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return await create_install_inquiry(email=payload.email, honeypot=payload.bot_field, source=source)
