"""Consistent characters and waste guards.

Patterns adopted (see docs/UGC_REFERENCE_MANIFEST.md rows added with this file):
- A character is a named *set of photos*; no model is trained (rosesfield
  characters, MIT @790d0dc). Higgsfield Elements likewise start from one image.
- Character sheet: portrait + full body on a plain grey background
  (OSideMedia/higgsfield-ai-prompt-skill, MIT @6a6a5dd, higgsfield-soul and
  higgsfield-character-design).
- Every shot prompt is split into an Identity Block (static descriptors only)
  and a Motion Block (camera/temporal only); never put age in a video prompt
  (same skill, "hard rule" for preventing identity drift).
- Never animate a "good enough" image: a hero frame (still) is approved before
  any paid video (higgsfield-pipeline). Scenes over 15 s are split.
- A shot holds at most 4 takes (comfield shots/takes, MIT @3dbae26; aftertake
  2-4 takes, MIT @0dc2f84). Broken shots are regenerated alone, never the set.

Everything here is pure validation or Redis bookkeeping. Nothing spends.
"""
from __future__ import annotations

import os

import httpx
import json
import re
import time
import uuid
from typing import Any

from . import usage_wallet as _wallet
from .media_generation import get_media_provider

KINDS = ("character", "product", "location")
MAX_PHOTOS = 12
MAX_TAKES_PER_SHOT = 4
MAX_SCENE_SECONDS = 15
_KEY = "buffer_blaster:identity:v1:"
_INDEX = "buffer_blaster:identity_index:v1"
_SHOT_KEY = "buffer_blaster:shot:v1:"

# Words that belong in the Motion Block, never the Identity Block.
_MOTION_TERMS = re.compile(
    r"\b(camera|dolly|pan|tilt|zoom|tracking|orbit|crane|handheld|push[- ]in|pull[- ]out|walks?|runs?|turns?|"
    r"moves?|moving|slow[- ]motion|cut to|transition|then|seconds?|fps)\b", re.I)
# Identity descriptors that cause drift when restated in the Motion Block.
_IDENTITY_TERMS = re.compile(
    r"\b(\d{1,2}[- ]?(year[- ]old|yo)|aged?\s+\d+|hair|eyes?|skin|freckles?|beard|tattoo|wearing|outfit|"
    r"ethnicity|complexion|face shape|jawline)\b", re.I)
_AGE_TERMS = re.compile(r"\b(\d{1,2}[- ]?(year[- ]old|yo)|aged?\s+\d+|teen(ager)?|elderly|middle[- ]aged)\b", re.I)


def _client():
    return _wallet._client()


async def _mirror_identity(record: dict[str, Any]) -> None:
    """Best-effort durable mirror into buffer_blaster.identities (migration 018).

    Same pattern as 016's agent audit mirror: Redis stays the runtime source
    of truth; a missing/unreachable Supabase never blocks identity work.
    """
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not (base and key):
        return
    row = {
        "id": record.get("id"), "kind": record.get("kind"), "name": record.get("name"),
        "photos": json.loads(record.get("photos") or "[]"), "sheet_url": record.get("sheet_url") or None,
        "identity_block": record.get("identity_block") or "", "created_by": record.get("created_by") or "",
        "deleted": record.get("deleted") == "1",
    }
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": "buffer_blaster",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            await http.post(f"{base}/rest/v1/identities?on_conflict=id", headers=headers,
                            json={**row, "workspace_id": _ws()})
    except httpx.HTTPError:
        return


def _ws() -> str:
    return _wallet._workspace_id()


def _https(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://") and len(url) <= 2048


# ------------------------------------------------------------ registry


def validate_identity(kind: str, name: str, photos: list[str], sheet_url: str | None) -> list[str]:
    problems: list[str] = []
    if kind not in KINDS:
        problems.append(f"kind must be one of {', '.join(KINDS)}")
    if not 2 <= len((name or "").strip()) <= 80:
        problems.append("name must be 2-80 characters")
    if not photos:
        problems.append("add at least one photo")
    if len(photos) > MAX_PHOTOS:
        problems.append(f"at most {MAX_PHOTOS} photos")
    if any(not _https(p) for p in photos):
        problems.append("photos must be https URLs from the asset store")
    if len(set(photos)) != len(photos):
        problems.append("duplicate photos")
    if sheet_url is not None and not _https(sheet_url):
        problems.append("sheet_url must be an https URL")
    return problems


async def create_identity(*, kind: str, name: str, photos: list[str], sheet_url: str | None = None,
                          identity_block: str = "", created_by: str) -> dict[str, Any]:
    problems = validate_identity(kind, name, photos, sheet_url)
    if identity_block:
        problems += [f"identity_block: {p}" for p in lint_identity_block(identity_block)]
    if problems:
        return {"ok": False, "error": "invalid_identity", "problems": problems}
    client = _client()
    if client is None:
        return {"ok": False, "error": "identity_store_unavailable"}
    identity_id = str(uuid.uuid4())
    record = {
        "id": identity_id, "kind": kind, "name": " ".join(name.split()), "photos": json.dumps(photos),
        "sheet_url": sheet_url or "", "identity_block": identity_block.strip(), "created_by": created_by,
        "created_at_epoch": str(int(time.time())), "workspace_id": _ws(), "deleted": "0",
    }
    try:
        await client.hset(f"{_KEY}{identity_id}", mapping=record)
        await client.hset(_INDEX, identity_id, kind)
    finally:
        await client.aclose()
    await _mirror_identity(record)
    return {"ok": True, "identity": _public(record)}


def _public(raw: dict[str, Any]) -> dict[str, Any]:
    photos = json.loads(raw.get("photos") or "[]")
    sheet = raw.get("sheet_url") or None
    return {
        "identity_id": raw.get("id"), "kind": raw.get("kind"), "name": raw.get("name"), "photos": photos,
        "sheet_url": sheet, "identity_block": raw.get("identity_block") or "",
        "consistency_ready": bool(sheet) or len(photos) >= 3,
        "next": None if (sheet or len(photos) >= 3) else "Add a character sheet or at least 3 angles (front, 3/4, side) for reliable consistency.",
    }


async def get_identity(identity_id: str) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "identity_store_unavailable"}
    try:
        raw = await client.hgetall(f"{_KEY}{identity_id}")
    finally:
        await client.aclose()
    if not raw or raw.get("workspace_id", "") != _ws() or raw.get("deleted") == "1":
        return {"ok": False, "error": "identity_not_found"}
    return {"ok": True, "identity": _public(raw)}


async def list_identities(kind: str | None = None) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "identity_store_unavailable"}
    try:
        rows = []
        for identity_id in await client.hgetall(_INDEX):
            raw = await client.hgetall(f"{_KEY}{identity_id}")
            if raw and raw.get("workspace_id", "") == _ws() and raw.get("deleted") != "1" and (not kind or raw.get("kind") == kind):
                rows.append(_public(raw))
        rows.sort(key=lambda r: r["name"] or "")
        return {"ok": True, "identities": rows}
    finally:
        await client.aclose()


async def update_identity(identity_id: str, *, add_photos: list[str] | None = None, remove_photos: list[str] | None = None,
                          sheet_url: str | None = None, identity_block: str | None = None) -> dict[str, Any]:
    client = _client()
    if client is None:
        return {"ok": False, "error": "identity_store_unavailable"}
    key = f"{_KEY}{identity_id}"
    try:
        raw = await client.hgetall(key)
        if not raw or raw.get("workspace_id", "") != _ws() or raw.get("deleted") == "1":
            return {"ok": False, "error": "identity_not_found"}
        photos = json.loads(raw.get("photos") or "[]")
        photos = [p for p in photos if p not in set(remove_photos or [])] + [p for p in (add_photos or []) if p not in photos]
        sheet = raw.get("sheet_url") or None if sheet_url is None else sheet_url
        block = raw.get("identity_block", "") if identity_block is None else identity_block
        problems = validate_identity(raw.get("kind", ""), raw.get("name", ""), photos, sheet or None)
        if block:
            problems += [f"identity_block: {p}" for p in lint_identity_block(block)]
        if problems:
            # Rosesfield rule: a character needs at least one photo.
            return {"ok": False, "error": "invalid_identity", "problems": problems}
        await client.hset(key, mapping={"photos": json.dumps(photos), "sheet_url": sheet or "", "identity_block": block})
        raw.update({"photos": json.dumps(photos), "sheet_url": sheet or "", "identity_block": block})
    finally:
        await client.aclose()
    await _mirror_identity(raw)
    return {"ok": True, "identity": _public(raw)}


# ------------------------------------------------- prompt discipline


def lint_identity_block(text: str) -> list[str]:
    hits = sorted({m.group(0).lower() for m in _MOTION_TERMS.finditer(text or "")})
    return [f"motion/camera words belong in the motion block: {', '.join(hits)}"] if hits else []


def lint_motion_block(text: str) -> list[str]:
    problems = []
    ages = sorted({m.group(0).lower() for m in _AGE_TERMS.finditer(text or "")})
    if ages:
        problems.append(f"never state age in a video prompt: {', '.join(ages)}")
    ident = sorted({m.group(0).lower() for m in _IDENTITY_TERMS.finditer(text or "")} - set(ages))
    if ident:
        problems.append(f"identity descriptors belong in the identity block (restating them causes drift): {', '.join(ident)}")
    return problems


def compile_shot_prompt(identity_block: str, motion_block: str, *, references: int = 0) -> dict[str, Any]:
    """Two-block prompt. Returns problems instead of a prompt when the split is violated."""
    problems = [f"identity_block: {p}" for p in lint_identity_block(identity_block)]
    problems += [f"motion_block: {p}" for p in lint_motion_block(motion_block)]
    if not identity_block.strip():
        problems.append("identity_block is empty")
    if not motion_block.strip():
        problems.append("motion_block is empty")
    if problems:
        return {"ok": False, "error": "prompt_split_violation", "problems": problems}
    ref = f"Keep the subject identical to reference image{'s' if references > 1 else ''} @1{'-@' + str(references) if references > 1 else ''}. " if references else ""
    return {"ok": True, "prompt": f"{ref}{identity_block.strip()}\n\n{motion_block.strip()}",
            "identity_block": identity_block.strip(), "motion_block": motion_block.strip()}


# ------------------------------------------------------- waste guard


def resolve_provider_caps(provider_caps: dict[str, Any] | None = None) -> dict[str, Any]:
    """Caps for shot_preflight, filled server-side from the active provider.

    When the media provider is configured, its env-driven capabilities
    (provider_registry / GENERATION_GATEWAY_SUPPORTED_* / FAL_*) ALWAYS win:
    callers never pass caps by hand, because permissive caller caps could
    skip waste guards in front of spend. With no configured provider
    (tests/dev), caller-supplied caps are used unchanged.
    """
    try:
        provider = get_media_provider()
    except Exception:
        provider = None
    if provider is not None and getattr(provider, "configured", False):
        caps = provider.capabilities()
        return {
            "provider": caps.provider,
            "server_derived": True,
            "supported_durations": list(caps.supported_durations_seconds),
            "supported_ratios": list(caps.supported_ratios),
            "accepts_image": bool(caps.image_to_video),
        }
    return {**dict(provider_caps or {}), "server_derived": False}



def shot_preflight(shot: dict[str, Any], *, identity: dict[str, Any] | None = None,
                   provider_caps: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every reason a paid video call would be wasted, checked before any spend.

    ``shot``: {"duration_seconds", "aspect_ratio", "hero_frame_approved", "hero_frame_url",
               "identity_block", "motion_block", "takes_existing", "takes_requested"}
    ``provider_caps``: {"supported_durations": [..], "supported_ratios": [..], "accepts_image": bool}
    """
    blockers: list[str] = []
    warnings: list[str] = []
    caps = resolve_provider_caps(provider_caps)
    duration = int(shot.get("duration_seconds") or 0)
    if duration <= 0:
        blockers.append("duration_seconds is required")
    elif duration > MAX_SCENE_SECONDS:
        blockers.append(f"scene is {duration}s; split it into scenes of {MAX_SCENE_SECONDS}s or less (prompt adherence degrades)")
    if caps.get("supported_durations") and duration and duration not in caps["supported_durations"]:
        blockers.append(f"model does not support {duration}s; supported: {caps['supported_durations']}")
    ratio = shot.get("aspect_ratio")
    if caps.get("supported_ratios") and ratio not in caps["supported_ratios"]:
        blockers.append(f"model does not support aspect ratio {ratio}; supported: {caps['supported_ratios']}")
    if not shot.get("hero_frame_approved") or not _https(str(shot.get("hero_frame_url") or "")):
        blockers.append("approve a hero frame (still) before generating video; never animate a good-enough image")
    if caps.get("accepts_image") is False:
        blockers.append("selected model cannot take the hero frame as an image input; pick an image-to-video model")
    prompt = compile_shot_prompt(str(shot.get("identity_block") or ""), str(shot.get("motion_block") or ""))
    if not prompt["ok"]:
        blockers += prompt["problems"]
    if identity is not None:
        if not identity.get("photos"):
            blockers.append("the selected character has no photos")
        elif not identity.get("consistency_ready"):
            warnings.append("character has fewer than 3 angles and no sheet; identity may drift")
    existing = int(shot.get("takes_existing") or 0)
    requested = int(shot.get("takes_requested") or 1)
    if requested < 1:
        blockers.append("takes_requested must be at least 1")
    if existing + requested > MAX_TAKES_PER_SHOT:
        blockers.append(f"a shot holds at most {MAX_TAKES_PER_SHOT} takes ({existing} exist); pick a take or start a new shot")
    return {"ok": not blockers, "blockers": blockers, "warnings": warnings,
            "compiled_prompt": prompt.get("prompt") if prompt["ok"] else None, "paid_generation": False,
            "provider_caps": caps}
