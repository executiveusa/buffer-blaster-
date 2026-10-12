"""Local stdio MCP transport for Claude Code, Codex, and other agents.

This is a transport adapter only: all tools and approvals remain on the
canonical Buffer Blaster API. Credentials are read from the process environment,
never from MCP messages or committed client configuration.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_MESSAGE_CHARS = 4_000_000
MAX_RESPONSE_BYTES = 4_000_000


class _RejectRedirects(HTTPRedirectHandler):
    """Never forward an operator bearer token to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _secure_open(request: Request, *, timeout: int):
    # The standard urlopen redirect handler can forward Authorization to a
    # different origin. Redirects must fail closed for operator credentials.
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _endpoint(base: str) -> str | None:
    base = base.rstrip("/")
    try:
        parts = urlsplit(base)
        hostname = parts.hostname
        _ = parts.port  # Validate malformed ports before constructing a request.
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc or not hostname or parts.username or parts.password or parts.query or parts.fragment:
        return None
    # Bearer credentials must never traverse plaintext network connections.
    if parts.scheme == "http" and hostname.lower() not in {"localhost", "127.0.0.1", "::1"}:
        return None
    return base if parts.path.endswith("/api/mcp") else f"{base}/api/mcp"


def forward(message: Any, *, base_url: str, token: str, opener=_secure_open) -> dict[str, Any] | None:
    """Forward one JSON-RPC message without granting new authority."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid Request")

    notification = "id" not in message
    request_id = message.get("id")
    if not token:
        return None if notification else _error(request_id, -32001, "BLASTER_API_KEY is not configured")

    endpoint = _endpoint(base_url)
    if endpoint is None:
        return None if notification else _error(request_id, -32002, "BLASTER_API_URL is invalid")

    request = Request(
        endpoint,
        data=json.dumps(message, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=180) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if notification:
                return None
            if len(payload) > MAX_RESPONSE_BYTES:
                return _error(request_id, -32003, "Buffer Blaster response exceeded size limit")
            result = json.loads(payload)
            if not isinstance(result, dict) or result.get("jsonrpc") != "2.0" or result.get("id") != request_id or not ("result" in result or "error" in result):
                return _error(request_id, -32003, "Invalid response from Buffer Blaster API")
            return result
    except HTTPError as exc:
        return None if notification else _error(request_id, -32004, f"Buffer Blaster API returned HTTP {exc.code}")
    except (URLError, TimeoutError, OSError):
        return None if notification else _error(request_id, -32005, "Buffer Blaster API unavailable")
    except (UnicodeError, ValueError, TypeError):
        return None if notification else _error(request_id, -32003, "Invalid response from Buffer Blaster API")


def serve(*, stdin: TextIO, stdout: TextIO, base_url: str, token: str, opener=_secure_open) -> None:
    """MCP stdio: one JSON-RPC object per line, no diagnostics on stdout."""
    for raw in stdin:
        if not raw.strip():
            continue
        if len(raw) > MAX_MESSAGE_CHARS:
            result = _error(None, -32600, "MCP request exceeded size limit")
        else:
            try:
                message = json.loads(raw)
            except (ValueError, UnicodeError):
                result = _error(None, -32700, "Parse error")
            else:
                result = forward(message, base_url=base_url, token=token, opener=opener)
        if result is not None:
            stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
            stdout.flush()


def main() -> None:
    serve(
        stdin=sys.stdin,
        stdout=sys.stdout,
        base_url=os.getenv("BLASTER_API_URL", "http://localhost:8000"),
        token=os.getenv("BLASTER_API_KEY", ""),
    )


if __name__ == "__main__":
    main()
