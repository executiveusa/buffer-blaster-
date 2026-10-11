from pathlib import Path

from starlette.requests import Request

from api.deps import _client_ip


def _request(client_host: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/verify",
        "headers": headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
        "http_version": "1.1",
    }
    return Request(scope)


def test_login_rate_limit_ignores_spoofed_x_forwarded_for():
    request = _request("203.0.113.10", "198.51.100.99")
    assert _client_ip(request) == "203.0.113.10"


def test_login_rate_limit_uses_direct_client_host():
    request = _request("203.0.113.11")
    assert _client_ip(request) == "203.0.113.11"


def test_production_uvicorn_does_not_trust_forwarded_headers_from_arbitrary_peers():
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(encoding="utf-8")
    assert "--proxy-headers" not in dockerfile
    assert "--forwarded-allow-ips" not in dockerfile
