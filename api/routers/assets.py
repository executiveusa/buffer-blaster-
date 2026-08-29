"""Reference asset routes for moodboards and future scene/actor workflows."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from ..services.integration_auth import verify_operator
from ..services.source_assets import create_uploaded_reference, create_url_reference, list_references

router = APIRouter(prefix="/api/studio/references", tags=["studio-references"])


class UrlReference(BaseModel):
    url: str
    label: str = ""
    kind: str = "reference"


@router.get("")
async def references(limit: int = 100, _=Depends(verify_operator)) -> dict:
    assets = await list_references(limit)
    return {"ok": True, "assets": assets, "count": len(assets)}


@router.post("/url")
async def add_url_reference(payload: UrlReference, _=Depends(verify_operator)) -> dict:
    return await create_url_reference(url=payload.url, kind=payload.kind, metadata={"label": payload.label})


@router.post("/upload")
async def upload_reference(
    file: UploadFile = File(...),
    label: str = Form(default=""),
    _=Depends(verify_operator),
) -> dict:
    allowed = {"image/jpeg", "image/png", "image/webp"}
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        return {"ok": False, "error": "unsupported_reference_type", "allowed": sorted(allowed)}
    suffix = Path(file.filename or "reference").suffix or ".bin"
    with tempfile.NamedTemporaryFile(prefix="bb-ref-", suffix=suffix, delete=False) as handle:
        temp = Path(handle.name)
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > 25 * 1024 * 1024:
                temp.unlink(missing_ok=True)
                return {"ok": False, "error": "reference_too_large", "limit_bytes": 25 * 1024 * 1024}
            handle.write(chunk)
    try:
        return await create_uploaded_reference(
            source=temp,
            filename=file.filename or "reference",
            content_type=content_type,
            metadata={"label": label},
        )
    finally:
        temp.unlink(missing_ok=True)
