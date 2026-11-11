"""Public install-interest intake. No operator secret is accepted or returned."""
from __future__ import annotations

from ..deps import _client_ip
from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..services.install_inquiries import create_install_inquiry

router = APIRouter(prefix="/api/install-inquiries", tags=["install-inquiries"])


class InquiryPayload(BaseModel):
    email: str
    bot_field: str = ""


@router.post("")
async def create(payload: InquiryPayload, request: Request) -> dict:
    source = _client_ip(request)
    return await create_install_inquiry(email=payload.email, honeypot=payload.bot_field, source=source)
