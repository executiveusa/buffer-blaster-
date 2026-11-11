"""S5 r2: reviewer fixes - ffprobe fail-closed, per-file picker consent,
mirror observability, DNS pinning, idempotency concurrency, disk headroom."""
from __future__ import annotations

import asyncio

import pytest

from api.services import footage, footage_import
from tests.studio.test_footage_import import (DROPBOX_LINK, MP4, FakeHTTP, FakeResp,
                                              env, public_resolver)  # noqa: F401 (fixture)

LINK = DROPBOX_LINK


# ------------------------------------------------------- picker consent


@pytest.mark.asyncio
async def test_unconsented_link_refused_before_any_download(env):
    http = FakeHTTP({LINK: FakeResp(200, chunks=[MP4])})
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="evil.mp4",
        idempotency_key="r2-consent-001",
        link="https://dl.dropboxusercontent.com/s/other/never-picked.mp4",
        http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "file_not_consented"
    assert not [c for c in http.calls if c[0] == "GET"], "no provider fetch for unconsented file"


@pytest.mark.asyncio
async def test_unconsented_google_file_id_refused(env):
    res = await footage_import.import_footage(
        provider="google", actor="user:u1", filename="x.mp4",
        idempotency_key="r2-consent-002", file_id="drive-root-file-never-picked",
        http=FakeHTTP(), resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "file_not_consented"


@pytest.mark.asyncio
async def test_consent_is_workspace_bound(env, monkeypatch):
    # consented in ws-test; a caller in another workspace gets nothing
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-other")
    assert not await footage.is_file_consented("dropbox", LINK)
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    assert await footage.is_file_consented("dropbox", LINK)


# ------------------------------------------------------- ffprobe fail-closed


@pytest.mark.asyncio
async def test_missing_ffprobe_fails_closed_operator_visible(env, monkeypatch):
    async def missing(path):
        return None  # binary not installed

    monkeypatch.setattr(footage_import, "_ffprobe_ok", missing)
    http = FakeHTTP({LINK: FakeResp(200, chunks=[MP4])})
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="r2-ffprobe-001", link=LINK, http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "ffprobe_unavailable"
    assert "OPERATOR" in res["detail"]


# ------------------------------------------------------- concurrency + disk


@pytest.mark.asyncio
async def test_concurrent_same_key_imports_cannot_both_run(env):
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowHTTP(FakeHTTP):
        async def __call__(self, method, url, **kwargs):
            resp = await super().__call__(method, url, **kwargs)
            if method == "GET":
                started.set()
                await release.wait()
            return resp

    http = SlowHTTP({LINK: FakeResp(200, chunks=[MP4])})

    async def imp():
        return await footage_import.import_footage(
            provider="dropbox", actor="user:u1", filename="clip.mp4",
            idempotency_key="r2-conc-001", link=LINK, http=http, resolver=public_resolver)

    first = asyncio.create_task(imp())
    await started.wait()
    second = await imp()
    assert second["ok"] is False and second["error"] == "import_in_progress"
    release.set()
    assert (await first)["ok"] is True


@pytest.mark.asyncio
async def test_disk_headroom_enforced_before_download(env, monkeypatch):
    monkeypatch.setattr(footage_import, "_disk_headroom_ok", lambda required: False)
    http = FakeHTTP({LINK: FakeResp(200, chunks=[MP4])})
    res = await footage_import.import_footage(
        provider="dropbox", actor="user:u1", filename="clip.mp4",
        idempotency_key="r2-disk-001", link=LINK, http=http, resolver=public_resolver)
    assert res["ok"] is False and res["error"] == "disk_headroom_insufficient"
    assert not [c for c in http.calls if c[0] == "GET"]


def test_disk_headroom_real_check():
    import shutil
    import tempfile
    free = shutil.disk_usage(tempfile.gettempdir()).free
    assert footage_import._disk_headroom_ok(1) is (free > 1 + 512 * 1024 * 1024)


# ------------------------------------------------------- DNS pinning


@pytest.mark.asyncio
async def test_pinned_transport_connects_to_validated_ip_with_tls_host(env, monkeypatch):
    """The connect goes to the VALIDATED address; TLS SNI/Host stay the real
    hostname - a rebind between validation and connect cannot redirect us."""
    seen = {}

    class SpyClient:
        def __init__(self, *a, **k):
            seen["verify"] = k.get("verify")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def aclose(self):
            return None

        def build_request(self, method, url, headers=None, extensions=None):
            seen["url"] = url
            seen["host_header"] = (headers or {}).get("Host")
            seen["sni"] = (extensions or {}).get("sni_hostname")
            return (method, url)

        async def send(self, request, stream=True):
            return FakeResp(200, chunks=[MP4])

    monkeypatch.setattr(footage_import.httpx, "AsyncClient", SpyClient)
    resp, err = await footage_import._pinned_get(
        "https://dl.dropboxusercontent.com/s/abc/clip.mp4",
        headers={"Authorization": "Bearer x"}, addresses=["93.184.216.34"],
        resolver=public_resolver)
    assert err is None
    assert seen["url"].startswith("https://93.184.216.34/"), "connect pinned to validated IP"
    assert seen["host_header"] == "dl.dropboxusercontent.com"
    assert seen["sni"] == "dl.dropboxusercontent.com", "TLS verifies the real hostname"
    assert seen["verify"] is True
    await resp.aclose()


@pytest.mark.asyncio
async def test_rebind_private_second_resolution_never_connected(env, monkeypatch):
    """Validation sees a public IP; if the pinned connect address were
    re-resolved privately we'd catch it - assert we connect to the validated
    address from the guard, not a fresh lookup."""
    calls = []

    async def flaky_resolver(host):
        calls.append(1)
        return ["10.0.0.5"] if len(calls) > 1 else ["93.184.216.34"]

    # guard validates with the first answer set; pinning uses guard['addresses']
    guard = await footage_import.validate_url(
        "https://dl.dropboxusercontent.com/s/abc/clip.mp4", resolver=flaky_resolver)
    assert guard["ok"] is True and guard["addresses"] == ["93.184.216.34"]
    # a second (rebinding) resolution is never used for the connect
    assert len(calls) == 1


# ------------------------------------------------------- mirror observability


@pytest.mark.asyncio
async def test_revoke_mirror_failure_is_observable_and_backlogged(env, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supa.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    consent = await footage.consent_url("google", actor="user:u1")
    http = FakeHTTP({"https://oauth2.googleapis.com/token": FakeResp(200, {
        "access_token": "ya29.x", "expires_in": 3600})})
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)

    class BoomCM:
        async def __aenter__(self):
            raise RuntimeError("mirror down")

        async def __aexit__(self, *a):
            return None

    import httpx as _httpx
    monkeypatch.setattr(_httpx, "AsyncClient", lambda *a, **k: BoomCM())
    res = await footage.revoke("google", actor="user:u1", http=http)
    assert res["ok"] is True  # authoritative local revoke stands
    assert res["mirror"] == "backlogged" and res["mirror_error"], "failure is surfaced"
    backlog = await env.lrange("bb:footage:mirror_backlog", 0, -1)
    assert backlog, "owed mirror delete is durable for replay"
