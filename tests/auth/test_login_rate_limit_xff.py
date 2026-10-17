from starlette.requests import Request

from api import deps


def _request(headers: list[tuple[bytes, bytes]], client: str = "203.0.113.10") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/verify",
            "headers": headers,
            "client": (client, 54321),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
            "root_path": "",
            "http_version": "1.1",
        }
    )


def test_login_rate_limit_ignores_spoofed_x_forwarded_for(monkeypatch):
    seen = []

    def fake_check_auth_rate_limit(client_ip):
        seen.append(client_ip)
        return True, 0

    monkeypatch.setattr(deps, "check_auth_rate_limit", fake_check_auth_rate_limit)
    monkeypatch.delenv("BLASTER_PROXY_SHARED_SECRET", raising=False)

    request = _request([(b"x-forwarded-for", b"198.51.100.99")])
    deps.rate_limit_auth(request)

    assert seen == ["203.0.113.10"]


def test_login_rate_limit_accepts_signed_frontend_client_ip(monkeypatch):
    seen = []

    def fake_check_auth_rate_limit(client_ip):
        seen.append(client_ip)
        return True, 0

    monkeypatch.setattr(deps, "check_auth_rate_limit", fake_check_auth_rate_limit)
    monkeypatch.setenv("BLASTER_PROXY_SHARED_SECRET", "server-secret")

    request = _request(
        [
            (b"x-buffer-blaster-proxy-secret", b"server-secret"),
            (b"x-buffer-blaster-client-ip", b"198.51.100.25"),
        ]
    )
    deps.rate_limit_auth(request)

    assert seen == ["198.51.100.25"]


def test_login_rate_limit_rejects_unsigned_or_malformed_forwarded_ip(monkeypatch):
    monkeypatch.setenv("BLASTER_PROXY_SHARED_SECRET", "server-secret")

    wrong_secret = _request(
        [
            (b"x-buffer-blaster-proxy-secret", b"attacker-value"),
            (b"x-buffer-blaster-client-ip", b"198.51.100.25"),
        ],
        client="203.0.113.11",
    )
    malformed = _request(
        [
            (b"x-buffer-blaster-proxy-secret", b"server-secret"),
            (b"x-buffer-blaster-client-ip", b"not-an-ip"),
        ],
        client="203.0.113.12",
    )

    assert deps._client_ip(wrong_secret) == "203.0.113.11"
    assert deps._client_ip(malformed) == "203.0.113.12"
