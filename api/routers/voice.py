"""Voice/text command router.

Browser speech, Telegram, glasses, or any other client can submit a transcript.
The server resolves it into the same explicit intents used by the studio. It
never publishes directly; scheduling still passes through the approval gate.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services.integration_auth import verify_operator
from ..services.voice_intent import parse_voice_intent

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceCommand(BaseModel):
    transcript: str
    source: str = "web"


@router.post("/command")
async def voice_command(payload: VoiceCommand, _=Depends(verify_operator)) -> dict:
    result = parse_voice_intent(payload.transcript)
    next_route = {
        "create_ugc": "/api/studio/ugc/prompt",
        "create_campaign": "/api/studio/campaigns/plan",
        "schedule_content": "/api/studio/social/schedule",
        "status": "/api/studio/status",
    }[result.intent]
    return {
        "received": result.transcript,
        "source": payload.source,
        "status": "resolved",
        "intent": result.intent,
        "entity": result.entity,
        "requires_approval": result.requires_approval,
        "next": next_route,
    }
