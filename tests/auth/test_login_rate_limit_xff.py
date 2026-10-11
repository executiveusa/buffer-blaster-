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
