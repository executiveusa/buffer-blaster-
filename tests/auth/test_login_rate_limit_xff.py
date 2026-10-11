from starlette.requests import Request

from api.deps import _client_ip


def test_login_rate_limit_ignores_spoofed_x_forwarded_for():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/verify",
            "headers": [(b"x-forwarded-for", b"203.0.113.99")],
            "client": ("198.51.100.42", 43210),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert _client_ip(request) == "198.51.100.42"


import asyncio

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def _scope(client_host: str, forwarded_for: str):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/verify",
        "raw_path": b"/api/auth/verify",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"x-forwarded-for", forwarded_for.encode("ascii"))],
        "client": (client_host, 43210),
        "server": ("testserver", 80),
    }


def test_proxy_middleware_ignores_forwarded_header_from_untrusted_peer():
    observed = []

    async def app(scope, receive, send):
        observed.append(_client_ip(Request(scope)))

    middleware = ProxyHeadersMiddleware(app, trusted_hosts="10.0.0.2")

    async def run():
        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            return None

        await middleware(_scope("198.51.100.42", "203.0.113.99"), receive, send)

    asyncio.run(run())
    assert observed == ["198.51.100.42"]


def test_proxy_middleware_accepts_forwarded_client_only_from_trusted_peer():
    observed = []

    async def app(scope, receive, send):
        observed.append(_client_ip(Request(scope)))

    middleware = ProxyHeadersMiddleware(app, trusted_hosts="10.0.0.2")

    async def run():
        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            return None

        await middleware(_scope("10.0.0.2", "203.0.113.99"), receive, send)

    asyncio.run(run())
    assert observed == ["203.0.113.99"]
