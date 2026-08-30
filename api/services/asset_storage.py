"""Durable asset storage for generated clips, seed frames, and final ads.

Supabase Storage is the production backend. Provider credentials are never sent
to asset hosts. Signed URLs are short-lived and generated on demand.
"""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx


class AssetStorage:
    def __init__(self) -> None:
        self.base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self.bucket = os.getenv("BUFFER_BLASTER_ASSET_BUCKET", "buffer-blaster-assets").strip() or "buffer-blaster-assets"
        self.max_download_bytes = int(os.getenv("ASSET_DOWNLOAD_MAX_BYTES", str(250 * 1024 * 1024)))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.service_key and self.bucket)

    def status(self) -> dict[str, Any]:
        return {
            "backend": "supabase-storage",
            "configured": self.configured,
            "bucket": self.bucket if self.configured else None,
        }

    def _headers(self, *, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def sign_path(self, object_name: str, *, expires_in: int = 3600) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "asset_storage_not_configured"}
        encoded = quote(object_name.lstrip("/"), safe="/")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/storage/v1/object/sign/{quote(self.bucket, safe='')}/{encoded}",
                headers={**self._headers(content_type="application/json")},
                json={"expiresIn": max(60, min(int(expires_in), 86_400))},
            )
        if response.is_error:
            return {"ok": False, "error": "asset_sign_failed", "status": response.status_code, "detail": response.text[:500]}
        payload = response.json()
        signed = payload.get("signedURL") or payload.get("signedUrl") or payload.get("signed_url")
        if not signed:
            return {"ok": False, "error": "asset_sign_missing_url"}
        if str(signed).startswith("http"):
            url = str(signed)
        else:
            url = f"{self.base_url}{signed if str(signed).startswith('/') else '/' + str(signed)}"
        return {"ok": True, "path": object_name, "signed_url": url, "expires_in": expires_in}

    async def upload_file(
        self,
        source: Path,
        *,
        object_name: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "error": "asset_storage_not_configured"}
        if not source.is_file():
            return {"ok": False, "error": "asset_source_missing", "path": str(source)}
        media_type = content_type or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        encoded = quote(object_name.lstrip("/"), safe="/")
        data = source.read_bytes()
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}/{encoded}",
                headers={**self._headers(content_type=media_type), "x-upsert": "true"},
                content=data,
            )
        if response.is_error:
            return {"ok": False, "error": "asset_upload_failed", "status": response.status_code, "detail": response.text[:500]}
        signed = await self.sign_path(object_name)
        return {
            "ok": True,
            "backend": "supabase-storage",
            "bucket": self.bucket,
            "path": object_name,
            "size_bytes": len(data),
            "content_type": media_type,
            "signed_url": signed.get("signed_url") if signed.get("ok") else None,
        }

    async def download_url(self, url: str, destination: Path) -> dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return {"ok": False, "error": "invalid_asset_url"}
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
                async with client.stream("GET", url, headers={"Accept": "*/*"}) as response:
                    if response.is_error:
                        return {"ok": False, "error": "asset_download_failed", "status": response.status_code}
                    with destination.open("wb") as handle:
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > self.max_download_bytes:
                                handle.close()
                                destination.unlink(missing_ok=True)
                                return {"ok": False, "error": "asset_too_large", "limit_bytes": self.max_download_bytes}
                            handle.write(chunk)
        except httpx.HTTPError as exc:
            destination.unlink(missing_ok=True)
            return {"ok": False, "error": "asset_download_failed", "detail": type(exc).__name__}
        return {"ok": True, "path": str(destination), "source_url": url, "size_bytes": total}


def get_asset_storage() -> AssetStorage:
    return AssetStorage()
