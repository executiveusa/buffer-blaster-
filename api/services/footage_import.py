"""S5: footage import worker.

Downloads a user-picked file from an allowlisted provider host into the asset
store with provenance. Guards, in order:

1. SSRF: https only, no userinfo, provider allowlist (dot-boundary suffix, so
   ``evil-googleapis.com`` fails), IP literals must be public, and DNS answers
   are checked so a public name resolving to a private address is rejected.
2. Redirects: followed manually (max 3), every hop re-validated by the same
   guard; ``follow_redirects`` is never enabled on the client.
3. Size: ``FOOTAGE_IMPORT_MAX_BYTES`` (default 2 GB). An oversized
   Content-Length is rejected before the body; streamed overflow aborts
   mid-transfer.
4. Content: magic-byte sniff for mp4/mov/webm/avi; markup bodies (auth error
   pages) are rejected; ffprobe validation when the binary is available.
5. Provenance: sha256 computed while streaming; the asset record carries
   source provider, remote file id, picked_by and the hash.

Imports are zero-cost transfers, not billable provider calls: they write no
usage-ledger rows. Caps guard spend, and there is no spend here.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import os
import re
import shutil
import socket
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import redis.asyncio as redis

from . import footage, source_assets

_DEFAULT_ALLOWED_HOSTS = (
    "googleapis.com",
    "dropboxusercontent.com",
    "graph.microsoft.com",
    "sharepoint.com",
    "onedrive.live.com",
    "1drv.live",
)
_MAX_REDIRECTS = 3
_VIDEO_SNIFFS = (
    (b"\x1a\x45\xdf\xa3", "video/webm"),   # EBML header: webm / mkv
)
_IMPORT_KIND = "footage_import"


def _max_bytes() -> int:
    try:
        return int(os.getenv("FOOTAGE_IMPORT_MAX_BYTES", "2000000000"))
    except ValueError:
        return 2_000_000_000


def _allowed_hosts() -> tuple[str, ...]:
    extra = os.getenv("FOOTAGE_IMPORT_ALLOWED_HOSTS", "")
    hosts = [h.strip().lower().rstrip(".") for h in extra.split(",") if h.strip()]
    return tuple(hosts) + _DEFAULT_ALLOWED_HOSTS


def _host_allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    for allowed in _allowed_hosts():
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def _public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified)


async def _default_resolver(host: str) -> list[str]:
    def _resolve() -> list[str]:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return sorted({info[4][0] for info in infos})
    return await asyncio.to_thread(_resolve)


async def validate_url(url: str, *, resolver: Any = None) -> dict[str, Any]:
    """SSRF guard. Returns {ok, host} or {ok: False, error}."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return {"ok": False, "error": "scheme_not_https"}
    if parsed.username or parsed.password:
        return {"ok": False, "error": "userinfo_not_allowed"}
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return {"ok": False, "error": "host_missing"}
    if not _host_allowed(host):
        return {"ok": False, "error": "host_not_allowed", "host": host}
    # IP literal: must be public. Hostname: every DNS answer must be public.
    try:
        ipaddress.ip_address(host)
        if not _public_ip(host):
            return {"ok": False, "error": "ip_not_public", "host": host}
        return {"ok": True, "host": host, "addresses": [host]}
    except ValueError:
        pass
    resolve = resolver or _default_resolver
    try:
        addresses = await resolve(host)
    except Exception:
        return {"ok": False, "error": "dns_resolution_failed", "host": host}
    if not addresses:
        return {"ok": False, "error": "dns_resolution_failed", "host": host}
    if not all(_public_ip(a) for a in addresses):
        return {"ok": False, "error": "dns_resolves_private", "host": host}
    return {"ok": True, "host": host, "addresses": list(addresses)}


def _sniff(head: bytes) -> str | None:
    """Magic-byte content type, or None when the head is not video."""
    if head.lstrip()[:1] == b"<":
        return "markup"  # HTML/XML error page, never footage
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video/mp4"  # also .mov / .m4v (ISO BMFF family)
    if head[:4] == b"RIFF" and len(head) >= 12 and head[8:12] == b"AVI ":
        return "video/avi"
    for magic, mime in _VIDEO_SNIFFS:
        if head[: len(magic)] == magic:
            return mime
    return None


async def _ffprobe_ok(path: Path) -> bool | None:
    """True/False from ffprobe; None when the binary is MISSING - callers
    must fail closed on None (operator-visible), never skip validation."""
    if not shutil.which("ffprobe"):
        return None
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=format_name",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate()
    return proc.returncode == 0 and bool(out.strip())


# ------------------------------------------------------- pinned transport
#
# DNS-rebind defense (S5 r2): validation resolves the host and checks every
# answer is public, but a plain httpx request would re-resolve at connect
# time - a rebinding attacker wins that race. The pinned transport connects
# to the VALIDATED address while TLS still verifies the real hostname:
# URL host = pinned IP, Host header + SNI (httpcore sni_hostname extension)
# = original host. An env allowlist entry only widens which hostnames pass
# validation; it never bypasses pinning.


async def _pinned_get(url: str, *, headers: dict[str, str], addresses: list[str],
                      resolver: Any) -> tuple[httpx.Response | None, dict[str, Any] | None]:
    """GET url connecting to the first validated address with TLS bound to
    the original hostname. Returns (response, None) or (None, error)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    try:
        ipaddress.ip_address(host)
        pin = host  # URL already carries the (validated public) IP literal
    except ValueError:
        pin = sorted(addresses)[0]  # deterministic choice among validated IPs
    pinned_url = parsed._replace(netloc=pin if parsed.port is None else f"{pin}:{parsed.port}").geturl()
    request_headers = {**headers, "Host": host if parsed.port is None else f"{host}:{parsed.port}"}
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=False, verify=True) as client:
            request = client.build_request("GET", pinned_url, headers=request_headers,
                                           extensions={"sni_hostname": host})
            response = await client.send(request, stream=True)
            # return the live streaming response; caller closes via aclose
            return _StreamingResponse(client, response), None
    except httpx.HTTPError as exc:
        return None, {"ok": False, "error": "pinned_connect_failed", "detail": type(exc).__name__}


class _StreamingResponse:
    """Keeps the pinned client alive for the streaming body."""

    def __init__(self, client: httpx.AsyncClient, response: httpx.Response):
        self._client = client
        self._response = response

    def __getattr__(self, item):
        return getattr(self._response, item)

    async def aclose(self) -> None:
        await self._response.aclose()
        await self._client.aclose()


def _disk_headroom_ok(required: int) -> bool:
    """Free space must cover the file plus a 512 MB working margin."""
    try:
        free = shutil.disk_usage(tempfile.gettempdir()).free
    except OSError:
        return False
    return free > required + 512 * 1024 * 1024


async def import_footage(*, provider: str, actor: str, filename: str,
                         idempotency_key: str, file_id: str | None = None,
                         link: str | None = None, http: Any = None,
                         resolver: Any = None) -> dict[str, Any]:
    """Import one picked file. Idempotent on (workspace, idempotency_key)."""
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", idempotency_key or ""):
        return {"ok": False, "error": "idempotency_key_invalid"}
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
    ws = footage._workspace_id()
    idem_key = f"bb:footage:import:{ws}:{idempotency_key}"
    replay = await r.get(idem_key)
    if replay:
        import json as _json
        prior = _json.loads(replay)
        prior["idempotent_replay"] = True
        return prior
    # Concurrency guard: one in-flight import per idempotency key. SET NX is
    # atomic, so two concurrent imports can never both run and last-write-win.
    lock_key = f"bb:footage:importlock:{ws}:{idempotency_key}"
    got_lock = await r.set(lock_key, "1", nx=True, px=600_000)
    if not got_lock:
        return {"ok": False, "error": "import_in_progress",
                "detail": "An import with this idempotency key is already running."}
    try:
        return await _import_locked(
            provider=provider, actor=actor, filename=filename,
            idempotency_key=idempotency_key, file_id=file_id, link=link,
            http=http, resolver=resolver, r=r, idem_key=idem_key)
    finally:
        await r.delete(lock_key)


async def _import_locked(*, provider: str, actor: str, filename: str,
                         idempotency_key: str, file_id: str | None,
                         link: str | None, http: Any, resolver: Any,
                         r: Any, idem_key: str) -> dict[str, Any]:
    # Picker consent (user requirement): the referenced file must have been
    # explicitly picked by a human in this workspace. Arbitrary file_ids or
    # un-picked links are refused before any provider call.
    if provider == "dropbox":
        consented_ref = link
    else:
        consented_ref = file_id
    if not await footage.is_file_consented(provider, consented_ref):
        return {"ok": False, "error": "file_not_consented",
                "detail": "Only files a human picked in this workspace can be imported; "
                          "register the pick via POST /api/studio/footage/picked first."}
    max_bytes = _max_bytes()
    if not _disk_headroom_ok(max_bytes):
        return {"ok": False, "error": "disk_headroom_insufficient",
                "detail": "Free disk must exceed the import cap plus a 512 MB margin."}

    target = await footage.download_target(provider, file_id=file_id, link=link, http=http)
    if not target.get("ok"):
        return target
    url, headers = target["url"], target["headers"]

    hops = 0
    while True:
        guard = await validate_url(url, resolver=resolver)
        if not guard.get("ok"):
            return guard
        if http is not None:
            resp = await http("GET", url, headers=headers, stream=True)
        else:
            resp, pin_error = await _pinned_get(
                url, headers=headers, addresses=guard.get("addresses", []),
                resolver=resolver or _default_resolver)
            if pin_error is not None:
                return pin_error
        status = getattr(resp, "status_code", 200)
        if status in (301, 302, 303, 307, 308):
            if hops >= _MAX_REDIRECTS:
                await resp.aclose()
                return {"ok": False, "error": "too_many_redirects"}
            location = resp.headers.get("location", "")
            if not location:
                await resp.aclose()
                return {"ok": False, "error": "redirect_without_location"}
            url = urljoin(url, location)
            headers = {}  # never forward provider auth headers to another hop
            hops += 1
            await resp.aclose()
            continue
        if status >= 400:
            await resp.aclose()
            return {"ok": False, "error": "download_failed", "status": status}
        break

    content_length = resp.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        return {"ok": False, "error": "file_too_large", "max_bytes": max_bytes,
                "content_length": int(content_length)}

    digest = hashlib.sha256()
    received = 0
    sniffed: str | None = None
    stream_error: dict[str, Any] | None = None
    fd, tmp_name = tempfile.mkstemp(prefix="bb-footage-", suffix=".bin")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        with tmp.open("wb") as fh:
            async for chunk in resp.aiter_bytes(1 << 16):
                received += len(chunk)
                if received > max_bytes:
                    stream_error = {"ok": False, "error": "file_too_large", "max_bytes": max_bytes}
                    break
                if sniffed is None:
                    sniffed = _sniff(chunk)
                    if sniffed == "markup":
                        stream_error = {"ok": False, "error": "not_video_markup_body"}
                        break
                fh.write(chunk)
                digest.update(chunk)
    finally:
        await resp.aclose()
    if stream_error is not None:
        tmp.unlink(missing_ok=True)
        return stream_error
    if sniffed is None:
        tmp.unlink(missing_ok=True)
        return {"ok": False, "error": "not_video_unrecognized_format"}

    probe = await _ffprobe_ok(tmp)
    if probe is None:
        tmp.unlink(missing_ok=True)
        return {"ok": False, "error": "ffprobe_unavailable",
                "detail": "OPERATOR: ffprobe is not installed on this host; footage imports "
                          "fail closed until it is (install ffmpeg)."}
    if probe is False:
        tmp.unlink(missing_ok=True)
        return {"ok": False, "error": "ffprobe_rejected"}

    record = await source_assets.create_uploaded_reference(
        source=tmp, filename=filename, content_type=sniffed,
        metadata={
            "source": provider,
            "remote_file_id": file_id,
            "picked_by": actor,
            "sha256": digest.hexdigest(),
            "bytes": received,
            "ffprobe": "passed",
        })
    tmp.unlink(missing_ok=True)
    if not record.get("ok"):
        return {"ok": False, "error": "asset_store_failed", "detail": record.get("error")}
    result = {
        "ok": True,
        "asset": record.get("asset"),
        "sha256": digest.hexdigest(),
        "bytes": received,
        "content_type": sniffed,
        "provider": provider,
        "usage_rows_written": 0,
    }
    import json as _json
    await r.set(idem_key, _json.dumps(result))
    return result
