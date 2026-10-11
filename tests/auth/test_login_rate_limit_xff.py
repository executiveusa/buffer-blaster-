from starlette.requests import Request

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
