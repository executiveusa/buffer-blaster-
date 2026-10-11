from pathlib import Path

import pytest
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api import deps


def test_client_ip_ignores_spoofed_x_forwarded_for_from_direct_client():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/verify",
            "headers": [(b"x-forwarded-for", b"203.0.113.99")],
            "client": ("10.0.0.5", 54321),
            "server": ("127.0.0.1", 8000),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert deps._client_ip(request) == "10.0.0.5"


@pytest.mark.asyncio
async def test_uvicorn_proxy_middleware_ignores_forwarded_ip_from_untrusted_peer():
    captured = {}

    async def app(scope, receive, send):
        captured["client"] = scope["client"]

    middleware = ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1")
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/verify",
        "headers": [(b"x-forwarded-for", b"203.0.113.99")],
        "client": ("10.0.0.5", 54321),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message):
        return None

    await middleware(scope, receive, send)

    assert captured["client"][0] == "10.0.0.5"


def test_dockerfile_does_not_trust_all_forwarded_peers():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "--forwarded-allow-ips='*'" not in dockerfile
    assert "FORWARDED_ALLOW_IPS=127.0.0.1" in dockerfile
