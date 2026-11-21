"""Locked, reusable ad characters ("house cast").

A character lives in ``characters/<id>/`` with a ``character.json`` (look,
wardrobe, setting, voice and delivery), reference images and a voice sample.
Selecting one on a UGC brief fills the actor, setting, delivery and
pronunciation fields so every ad uses the same person and voice.

Nothing here calls a provider or spends money.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CHARACTERS_DIR = Path(os.getenv("CHARACTERS_DIR", Path(__file__).resolve().parents[2] / "characters"))
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
DEFAULT_ACTOR = "a natural creator speaking like they are sharing something they actually use"
DEFAULT_DELIVERY = "calm, honest and direct"


def _dir(character_id: str) -> Path:
    if not _ID.match(character_id or ""):
        raise ValueError("unknown_character")
    path = CHARACTERS_DIR / character_id
    if not (path / "character.json").is_file():
        raise ValueError("unknown_character")
    return path


@lru_cache(maxsize=32)
def load_character(character_id: str) -> dict[str, Any]:
    path = _dir(character_id)
    data = json.loads((path / "character.json").read_text(encoding="utf-8"))
    data["id"] = character_id
    return data


def list_characters() -> list[dict[str, Any]]:
    if not CHARACTERS_DIR.is_dir():
        return []
    out = []
    for child in sorted(CHARACTERS_DIR.iterdir()):
        if (child / "character.json").is_file():
            c = load_character(child.name)
            out.append({"id": c["id"], "name": c.get("name", c["id"]), "voice_locked": bool(saved_voice_id(c))})
    return out


def reference_paths(character: dict[str, Any]) -> list[Path]:
    """Frontal reference first, then the extra angles."""
    base = _dir(character["id"])
    refs = character.get("references", {})
    names = [refs.get("frontal", "")] + list(refs.get("extra", []))
    return [base / name for name in names if name and (base / name).is_file()]


def voice_sample_path(character: dict[str, Any]) -> Path | None:
    name = character.get("voice", {}).get("clone_source")
    path = _dir(character["id"]) / name if name else None
    return path if path and path.is_file() else None


def saved_voice_id(character: dict[str, Any]) -> str:
    """The saved Kling voice id: env var first (set after the paid clone), then the file."""
    voice = character.get("voice", {})
    env_name = voice.get("kling_voice_id_env") or ""
    return (os.getenv(env_name, "") if env_name else "").strip() or str(voice.get("kling_voice_id") or "").strip()


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _join(*parts: str, sep: str = " ") -> str:
    return sep.join(p.strip().rstrip(".;") + ("." if sep == " " else "") for p in parts if p and p.strip())


def spoken(text: str, character: dict[str, Any]) -> str:
    """Swap brand names for the phonetic spelling the model should say."""
    for word, sound in (character.get("spoken_spellings") or {}).items():
        text = re.sub(rf"\b{re.escape(word)}\b", sound, text, flags=re.IGNORECASE)
    return text


def apply_character(fields: dict[str, Any]) -> dict[str, Any]:
    """Fill brief fields from the selected character. The brief's own non-default values win,
    except pronunciation and avoid, which are merged so the character's rules always apply."""
    character_id = str(fields.get("character") or "").strip()
    if not character_id:
        return fields
    c = load_character(character_id)
    out = dict(fields)
    out["character"] = character_id
    if not out.get("actor_description") or out["actor_description"] == DEFAULT_ACTOR:
        out["actor_description"] = c["actor_description"]
    if not out.get("delivery_tone") or out["delivery_tone"] == DEFAULT_DELIVERY:
        out["delivery_tone"] = c["delivery_tone"]
    if not out.get("setting"):
        out["setting"] = c.get("setting", "")
    out["pronunciation_notes"] = _join(c.get("pronunciation_notes", ""), out.get("pronunciation_notes", ""))
    out["avoid"] = _join(c.get("avoid", ""), out.get("avoid", ""), sep="; ")
    out["voice_description"] = c.get("voice_description", "")
    return out


def kling_elements(character: dict[str, Any]) -> list[dict[str, Any]]:
    """Kling v3 `elements` entry binding Jalen's face and saved voice. Empty until a voice id exists."""
    voice_id = saved_voice_id(character)
    refs = reference_paths(character)
    if not voice_id or not refs:
        return []
    return [{
        "frontal_image_url": data_uri(refs[0]),
        "reference_image_urls": [data_uri(p) for p in refs[1:4]] or [data_uri(refs[0])],
        "voice_id": voice_id,
    }]
