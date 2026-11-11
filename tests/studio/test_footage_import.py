"""S5: import worker - SSRF guard, redirects, size cap, MIME sniff,
idempotency, provenance, zero usage rows."""
from __future__ import annotations

import hashlib

import fakeredis
import pytest

from api.services import footage, footage_import, source_assets

MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64
WEBM = b"\x1a\x45\xdf\xa3" + b"\x01" * 60
GOOD_IPS = ["93.184.216.34"]


async def public_resolver(host):
    return GOOD_IPS


DROPBOX_LINK = "https://dl.dropboxusercontent.com/s/abc/clip.mp4"


@pytest.fixture
async def env(monkeypatch):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(footage.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(footage_import.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(source_assets.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", "test-master-key")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "gid-123")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "gsecret")

    async def _probe_ok(path):  # r2: ffprobe fail-closed - tests must pass, never skip
        return True
    monkeypatch.setattr(footage_import, "_ffprobe_ok", _probe_ok)

    class FakeStorage:
        configured = True

        async def upload_file(self, source, *, object_name, content_type):
            return {"ok": True, "path": object_name, "signed_url": "https://signed.test/x"}

    monkeypatch.setattr(source_assets, "get_asset_storage", lambda: FakeStorage())
    # r2: picker consent is a precondition - register the standard picks.
    await footage.register_picked_file("dropbox", file_ref=DROPBOX_LINK,
                                       filename="clip.mp4", actor="user:u1")
    await footage.register_picked_file("google", file_ref="f1",
                                       filename="clip.mp4", actor="user:u1")
    return fake


class FakeResp:
    def __init__(self, status_code=200, body=None, headers=None, chunks=None):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.headers = headers or {}
        self._chunks = chunks or []

    def json(self):
        return self._body

    async def aiter_bytes(self, n=65536):
        for c in self._chunks:
            yield c

    async def aclose(self):
        pass


class FakeHTTP:
    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    async def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        route = self.routes.get(url)
        if route is None:
            return FakeResp(404)
        if callable(route):
            return route(method, url, kwargs)
        return route


# ---------------------------------------------------------------- SSRF guard


@pytest.mark.asyncio
@pytest.mark.parametrize("url,error", [
    ("http://dl.dropboxusercontent.com/x.mp4", "scheme_not_https"),
    ("https://user:pw@dl.dropboxusercontent.com/x.mp4", "userinfo_not_allowed"),
    ("https://evil.example.com/x.mp4", "host_not_allowed"),
    ("https://evil-googleapis.com/x.mp4", "host_not_allowed"),
    ("https://127.0.0.1/x.mp4", "host_not_allowed"),
    ("https://169.254.169.254/latest/meta-data", "host_not_allowed"),
])
async def test_validate_url_rejects(url, error, env):
    res = await footage_import.validate_url(url, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == error


@pytest.mark.asyncio
async def test_allowlisted_subdomain_accepted(env):
    res = await footage_import.validate_url("https://www.googleapis.com/drive/v3/files/f1?alt=media",
                                            resolver=public_resolver)
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_dns_resolving_to_private_ip_rejected(env):
    async def evil_resolver(host):
        return ["10.0.0.4"]
    res = await footage_import.validate_url("https://www.googleapis.com/x", resolver=evil_resolver)
    assert res["ok"] is False and res["error"] == "dns_resolves_private"


@pytest.mark.asyncio
async def test_dns_failure_rejected(env):
    async def broken(host):
        raise OSError("no dns")
    res = await footage_import.validate_url("https://www.googleapis.com/x", resolver=broken)
    assert res["ok"] is False and res["error"] == "dns_resolution_failed"


# ---------------------------------------------------------------- import


def _dropbox_http(chunks, **kw):
    return FakeHTTP({DROPBOX_LINK:
                     FakeResp(200, chunks=chunks, **kw)})


@pytest.mark.asyncio
async def test_dropbox_import_success_with_provenance(env):
    http = _dropbox_http([MP4])
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0001", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is True
    assert res["sha256"] == hashlib.sha256(MP4).hexdigest()
    assert res["bytes"] == len(MP4)
    assert res["content_type"] == "video/mp4"
    meta = res["asset"]["metadata"]
    assert meta["source"] == "dropbox" and meta["picked_by"] == "user:u1"
    assert meta["sha256"] == res["sha256"]
    assert res["usage_rows_written"] == 0


@pytest.mark.asyncio
async def test_import_is_idempotent(env):
    http = _dropbox_http([MP4])
    first = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0002", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    second = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0002", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert second["idempotent_replay"] is True
    assert second["asset"]["id"] == first["asset"]["id"]
    assert len([c for c in http.calls if c[0] == "GET"]) == 1


@pytest.mark.asyncio
async def test_content_length_over_cap_rejected_before_body(env, monkeypatch):
    monkeypatch.setenv("FOOTAGE_IMPORT_MAX_BYTES", "10")
    http = _dropbox_http([MP4], headers={"content-length": str(len(MP4))})
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0003", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "file_too_large"


@pytest.mark.asyncio
async def test_streamed_overflow_aborts(env, monkeypatch):
    monkeypatch.setenv("FOOTAGE_IMPORT_MAX_BYTES", "10")
    http = _dropbox_http([MP4])  # no content-length header
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0004", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "file_too_large"


@pytest.mark.asyncio
async def test_markup_error_page_rejected(env):
    http = _dropbox_http([b"<html><body>401 Unauthorized</body></html>"])
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0005", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "not_video_markup_body"


@pytest.mark.asyncio
async def test_unrecognized_format_rejected(env):
    http = _dropbox_http([b"\x89\x50\x4e\x47random-bytes"])
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0006", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "not_video_unrecognized_format"


@pytest.mark.asyncio
async def test_webm_magic_accepted(env):
    http = _dropbox_http([WEBM])
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.webm",
        idempotency_key="imp-test-0007", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is True and res["content_type"] == "video/webm"


@pytest.mark.asyncio
async def test_redirect_off_allowlist_rejected_and_auth_not_forwarded(env):
    http = FakeHTTP({
        "https://dl.dropboxusercontent.com/s/abc/clip.mp4":
            FakeResp(302, headers={"location": "https://evil.example.com/steal"}),
    })
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0008", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "host_not_allowed"
    assert len(http.calls) == 1  # redirect target never requested


@pytest.mark.asyncio
async def test_redirect_within_allowlist_succeeds_without_forwarding_headers(env):
    http = FakeHTTP({
        "https://dl.dropboxusercontent.com/s/abc/clip.mp4":
            FakeResp(302, headers={"location": "https://content.dropboxusercontent.com/cd/get/clip.mp4"}),
        "https://content.dropboxusercontent.com/cd/get/clip.mp4":
            FakeResp(200, chunks=[MP4]),
    })
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0009", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is True
    assert http.calls[1][2]["headers"] == {}  # provider auth headers never forwarded


@pytest.mark.asyncio
async def test_too_many_redirects(env):
    hop = FakeResp(302, headers={"location": "https://dl.dropboxusercontent.com/s/abc/clip.mp4"})
    http = _dropbox_http(None)
    http.routes["https://dl.dropboxusercontent.com/s/abc/clip.mp4"] = hop
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0010", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "too_many_redirects"


@pytest.mark.asyncio
async def test_google_import_requires_connection(env):
    res = await footage_import.import_footage(
        provider="google", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0011", file_id="f1",
        http=FakeHTTP(), resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "not_connected"


@pytest.mark.asyncio
async def test_google_import_uses_encrypted_token(env):
    # connect google with a scripted token endpoint
    consent = await footage.consent_url("google", actor="user:u1")
    http = FakeHTTP({"https://oauth2.googleapis.com/token": FakeResp(200, {
        "access_token": "ya29.imp", "expires_in": 3600}),
        "https://www.googleapis.com/drive/v3/files/f1?alt=media": FakeResp(200, chunks=[MP4])})
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    res = await footage_import.import_footage(
        provider="google", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0012", file_id="f1",
        http=http, resolver=public_resolver)
    assert res["ok"] is True
    dl = [c for c in http.calls if "alt=media" in c[1]][0]
    assert dl[2]["headers"]["Authorization"] == "Bearer ya29.imp"


@pytest.mark.asyncio
async def test_import_writes_no_usage_rows(env):
    from api.services import usage_ledger
    import fakeredis as _fr
    fake2 = _fr.FakeAsyncRedis(decode_responses=True)
    usage_ledger.redis.from_url = lambda *a, **k: fake2
    http = _dropbox_http([MP4])
    await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0013", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert await usage_ledger.list_events() == []


@pytest.mark.asyncio
async def test_bad_idempotency_key_rejected(env):
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="bad", link=DROPBOX_LINK,
        http=FakeHTTP(), resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "idempotency_key_invalid"


@pytest.mark.asyncio
async def test_ffprobe_rejection_blocks_import(env, monkeypatch):
    async def reject(path):
        return False
    monkeypatch.setattr(footage_import, "_ffprobe_ok", reject)
    http = _dropbox_http([MP4])
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="imp-test-0014", link=DROPBOX_LINK,
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "ffprobe_rejected"
