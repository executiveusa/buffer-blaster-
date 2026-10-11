from starlette.requests import Request

from api import deps


def test_login_rate_limit_ignores_spoofed_x_forwarded_for(monkeypatch):
    seen = []

    def fake_check_auth_rate_limit(client_ip):
        seen.append(client_ip)
        return True, 0

    monkeypatch.setattr(deps, "check_auth_rate_limit", fake_check_auth_rate_limit)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/verify",
            "headers": [(b"x-forwarded-for", b"198.51.100.99")],
            "client": ("203.0.113.10", 54321),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
            "root_path": "",
            "http_version": "1.1",
        }
    )

    deps.rate_limit_auth(request)

    assert seen == ["203.0.113.10"]
