"""Voice router — webhook for Telegram + Meta glasses (VisionClaw).

Receives a transcript + intent + entity, dispatches to Hermes. In demo mode it
echoes back a canned response so the dashboard can show the wiring.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import verify_session

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceCommand(BaseModel):
    transcript: str
    source: str = "telegram"   # "telegram" | "glasses"
    intent: str | None = None
    entity: str | None = None


@router.post("/command")
async def voice_command(payload: VoiceCommand, _=Depends(verify_session)) -> dict:
    transcript = payload.transcript.strip()
    return {
        "received": transcript,
        "source": payload.source,
        "status": "queued",
        "response": (
            f"Got it. \"{transcript}\" is queued. "
            "Hermes activates on the VPS — see docs/HANDOFF.md."
        ),
    }
