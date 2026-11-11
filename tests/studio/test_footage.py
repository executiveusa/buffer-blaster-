"""S5: footage connectors - encrypted token storage, consent/revoke flows,
per-workspace isolation, Dropbox chooser (no stored token), MCP surface."""
from __future__ import annotations

import hashlib
import json

import fakeredis
import pytest

from api.services import footage, footage_import, runtime_settings


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
    """url -> FakeResp | callable(method, url, kwargs) -> FakeResp."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    async def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        route = self.routes.get(url)
        if route is None:
            return FakeResp(404, {"error": "not_found"})
        if callable(route):
            return route(method, url, kwargs)
        return route


@pytest.fixture
def redis_fake(monkeypatch):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(footage.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(footage_import.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(runtime_settings.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", "test-master-key")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "gid-123")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "gsecret")
    monkeypatch.setenv("ONEDRIVE_CLIENT_ID", "oid-123")
    monkeypatch.setenv("ONEDRIVE_CLIENT_SECRET", "osecret")
    monkeypatch.setenv("DROPBOX_APP_KEY", "dbx-app-key")
    return fake


# ---------------------------------------------------------------- consent


@pytest.mark.asyncio
async def test_google_consent_url_uses_drive_file_scope_and_hides_secret(redis_fake):
    res = await footage.consent_url("google", actor="user:u1")
    assert res["ok"] is True
    url = res["consent_url"]
    from urllib.parse import parse_qs, urlparse
    qs = parse_qs(urlparse(url).query)
    assert qs["scope"] == ["https://www.googleapis.com/auth/drive.file"]
    assert qs["client_id"] == ["gid-123"]
    assert "gsecret" not in json.dumps(res)
    assert res["state"]


@pytest.mark.asyncio
async def test_onedrive_consent_url_scopes(redis_fake):
    res = await footage.consent_url("onedrive", actor="user:u1")
    assert res["ok"] is True
    assert "Files.Read" in res["consent_url"]
    assert "osecret" not in json.dumps(res)


@pytest.mark.asyncio
async def test_dropbox_chooser_stores_no_token(redis_fake):
    res = await footage.consent_url("dropbox", actor="user:u1")
    assert res["ok"] is True and res["mode"] == "chooser"
    assert res["chooser_app_key"] == "dbx-app-key"
    assert res["consent_url"] is None
    keys = await redis_fake.keys("bb:footage:conn:*")
    assert keys == []  # nothing stored


@pytest.mark.asyncio
async def test_unconfigured_provider_rejected(redis_fake, monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET")
    res = await footage.consent_url("google", actor="user:u1")
    assert res["ok"] is False and res["error"] == "provider_not_configured"


@pytest.mark.asyncio
async def test_unknown_provider_rejected(redis_fake):
    res = await footage.consent_url("vimeo", actor="user:u1")
    assert res["ok"] is False and res["error"] == "unknown_provider"


# ---------------------------------------------------------------- connect


def _google_token_http(http: FakeHTTP):
    http.routes["https://oauth2.googleapis.com/token"] = FakeResp(200, {
        "access_token": "ya29.plaintext-access", "refresh_token": "r.plaintext-refresh",
        "expires_in": 3600, "scope": "https://www.googleapis.com/auth/drive.file"})
    return http


@pytest.mark.asyncio
async def test_complete_connect_encrypts_tokens_at_rest(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    res = await footage.complete_connect("google", code="auth-code", state=consent["state"],
                                         actor="user:u1", http=http)
    assert res["ok"] is True and res["connected"] is True
    raw = await redis_fake.get("bb:footage:conn:ws-test:google")
    assert raw is not None
    assert "ya29.plaintext-access" not in raw and "r.plaintext-refresh" not in raw
    record = json.loads(raw)
    assert record["token_ciphertext"] and record["refresh_ciphertext"]
    # round-trips through the AES-GCM core
    enc = footage._enc()
    assert enc.decrypt(record["token_ciphertext"]) == "ya29.plaintext-access"
    assert "ya29" not in json.dumps(res)  # response carries no token material


@pytest.mark.asyncio
async def test_state_is_single_use(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    first = await footage.complete_connect("google", code="c", state=consent["state"],
                                           actor="user:u1", http=http)
    assert first["ok"] is True
    again = await footage.complete_connect("google", code="c", state=consent["state"],
                                           actor="user:u1", http=http)
    assert again["ok"] is False and again["error"] == "state_invalid_or_expired"


@pytest.mark.asyncio
async def test_state_mismatch_provider_rejected(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    res = await footage.complete_connect("onedrive", code="c", state=consent["state"],
                                         actor="user:u1", http=FakeHTTP())
    assert res["ok"] is False and res["error"] == "state_mismatch"


@pytest.mark.asyncio
async def test_status_never_exposes_token_material(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    status = await footage.connection_status()
    body = json.dumps(status)
    assert status["connections"]["google"]["connected"] is True
    assert "ya29" not in body and "plaintext" not in body and "ciphertext" not in body


@pytest.mark.asyncio
async def test_workspace_isolation(redis_fake, monkeypatch):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-other")
    status = await footage.connection_status()
    assert status["connections"]["google"]["connected"] is False
    assert await footage._load_record("google") is None
    tok = await footage._access_token("google", http=http)
    assert tok["ok"] is False and tok["error"] == "not_connected"


@pytest.mark.asyncio
async def test_revoke_google_calls_upstream_and_deletes(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    http.routes["https://oauth2.googleapis.com/revoke"] = FakeResp(200, {})
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    res = await footage.revoke("google", actor="user:u1", http=http)
    assert res["ok"] is True and res["revoked"] is True and res["upstream"] == "revoked"
    revoke_calls = [c for c in http.calls if "revoke" in c[1]]
    assert revoke_calls and revoke_calls[0][2]["data"]["token"] == "ya29.plaintext-access"
    assert await redis_fake.get("bb:footage:conn:ws-test:google") is None


@pytest.mark.asyncio
async def test_revoke_dropbox_is_documented_noop(redis_fake):
    http = FakeHTTP()
    res = await footage.revoke("dropbox", actor="user:u1", http=http)
    assert res["ok"] is True and res["revoked"] is True
    assert http.calls == []  # nothing stored, nothing called


@pytest.mark.asyncio
async def test_revoke_when_not_connected(redis_fake):
    res = await footage.revoke("google", actor="user:u1", http=FakeHTTP())
    assert res["ok"] is True and res["was_connected"] is False


# ---------------------------------------------------------------- listing


@pytest.mark.asyncio
async def test_list_files_shows_only_human_picked(redis_fake):
    # r2: no whole-drive browse - the list comes from the picker-consent
    # registry, never from a provider listing call.
    http = _google_token_http(FakeHTTP())
    await footage.register_picked_file("google", file_ref="f1", filename="clip.mp4",
                                       actor="user:u1")
    res = await footage.list_files("google", http=http)
    assert res["ok"] is True
    assert res["files"] == [{"id": "f1", "name": "clip.mp4",
                             "picked_by": "user:u1", "picked_at": res["files"][0]["picked_at"]}]
    assert not [c for c in http.calls if "drive/v3/files?" in c[1]], "no provider browse"


@pytest.mark.asyncio
async def test_list_files_dropbox_chooser_note(redis_fake):
    res = await footage.list_files("dropbox")
    assert res["ok"] is True and res["files"] == [] and "note" in res


@pytest.mark.asyncio
async def test_list_files_without_picks_is_empty_not_error(redis_fake):
    res = await footage.list_files("onedrive", http=FakeHTTP())
    assert res["ok"] is True and res["files"] == [] and "no whole-drive" in res["note"]


@pytest.mark.asyncio
async def test_state_binds_initiating_actor(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    res = await footage.complete_connect("google", code="c", state=consent["state"],
                                         actor="user:attacker", http=FakeHTTP())
    assert res["ok"] is False and res["error"] == "state_mismatch"


@pytest.mark.asyncio
async def test_pkce_challenge_in_url_and_verifier_in_exchange(redis_fake):
    import base64 as _b64
    from urllib.parse import parse_qs, urlparse
    consent = await footage.consent_url("google", actor="user:u1")
    query = parse_qs(urlparse(consent["consent_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    challenge = query["code_challenge"][0]
    captured = {}

    class CapHTTP(FakeHTTP):
        async def __call__(self, method, url, **kwargs):
            captured.update(kwargs.get("data") or {})
            return await super().__call__(method, url, **kwargs)

    http = _google_token_http(CapHTTP())
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    verifier = captured.get("code_verifier", "")
    assert 43 <= len(verifier) <= 128
    digest = _b64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert digest == challenge  # RFC 7636 S256 binding


@pytest.mark.asyncio
async def test_expired_token_refreshes_via_refresh_token(redis_fake):
    consent = await footage.consent_url("google", actor="user:u1")
    http = _google_token_http(FakeHTTP())
    await footage.complete_connect("google", code="c", state=consent["state"],
                                   actor="user:u1", http=http)
    # force expiry, then add refresh response
    raw = json.loads(await redis_fake.get("bb:footage:conn:ws-test:google"))
    raw["expires_at"] = 1
    await redis_fake.set("bb:footage:conn:ws-test:google", json.dumps(raw))
    http.routes["https://oauth2.googleapis.com/token"] = FakeResp(200, {
        "access_token": "ya29.fresh", "expires_in": 3600})
    tok = await footage._access_token("google", http=http)
    assert tok["ok"] is True and tok["access_token"] == "ya29.fresh"
    refreshed = json.loads(await redis_fake.get("bb:footage:conn:ws-test:google"))
    assert "ya29.fresh" not in json.dumps(refreshed)  # stored encrypted again


# ---------------------------------------------------------------- MCP wiring


def test_mcp_tools_registered_with_correct_scopes():
    from api.routers import mcp
    names = {t["name"] for t in mcp.MCP_TOOLS}
    assert {"connect_source", "list_footage", "import_footage"} <= names
    assert mcp.tool_scope("list_footage") == "read"
    assert mcp.tool_scope("connect_source") == "plan"
    assert mcp.tool_scope("import_footage") == "plan"
    assert "connect_source" in mcp.MCP_WRITE_TOOLS
    assert "import_footage" in mcp.MCP_WRITE_TOOLS


def test_mcp_connect_source_schema_describes_consent_only():
    from api.routers import mcp
    tool = next(t for t in mcp.MCP_TOOLS if t["name"] == "connect_source")
    assert "consent URL only" in tool["description"]
    assert tool["inputSchema"]["required"] == ["provider"]
