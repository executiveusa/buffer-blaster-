"""Deterministic voice/text intent routing for the operator command surface."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class VoiceIntent:
    intent: str
    entity: str
    requires_approval: bool
    transcript: str


def parse_voice_intent(transcript: str) -> VoiceIntent:
    text = " ".join(transcript.strip().split())
    lower = text.lower()
    if any(word in lower for word in ("schedule", "publish", "post now", "send live")):
        intent = "schedule_content"
        requires_approval = True
    elif any(word in lower for word in ("ugc", "video ad", "creator ad", "unboxing", "testimonial video")):
        intent = "create_ugc"
        requires_approval = False
    elif any(word in lower for word in ("campaign", "launch", "content plan", "seven day", "7 day", "30 day")):
        intent = "create_campaign"
        requires_approval = False
    elif any(word in lower for word in ("status", "what's running", "whats running", "queue")):
        intent = "status"
        requires_approval = False
    else:
        intent = "create_campaign"
        requires_approval = False

    entity = text
    match = re.search(r"\bfor\s+(.+?)(?:\s+for\s+(?:instagram|facebook|tiktok|linkedin|youtube|x)\b|$)", text, re.I)
    if match:
        entity = match.group(1).strip()
    return VoiceIntent(intent=intent, entity=entity, requires_approval=requires_approval, transcript=text)
