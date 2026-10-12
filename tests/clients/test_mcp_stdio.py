"""Transport regression tests: stdio adapter never weakens API approval/auth."""
import io
import json
from urllib.error import HTTPError, URLError

from cli.mcp_stdio import forward, serve


class Response:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.data


def test_initialize_and_tools_list_forward_with_env_token_not_stdout():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        message = json.loads(request.data)
        return Response(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {"tools": []}}).encode())

    stdin = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
        '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
    )
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout, base_url="https://blaster.example", token="private-test-token", opener=opener)

    output = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [item["id"] for item in output] == [1, 2]
    assert len(calls) == 2
    assert all(req.full_url == "https://blaster.example/api/mcp" for req, _ in calls)
    assert all(req.get_header("Authorization") == "Bearer private-test-token" for req, _ in calls)
    assert "private-test-token" not in stdout.getvalue()


def test_initialized_notification_produces_no_stdout():
    def opener(_request, timeout):
        return Response(b"")

    output = io.StringIO()
    serve(
        stdin=io.StringIO('{"jsonrpc":"2.0","method":"notifications/initialized"}\n'),
        stdout=output, base_url="http://localhost:8000", token="test", opener=opener,
    )
    assert output.getvalue() == ""


def test_missing_token_fails_closed_without_network_call():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    request = {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "execute_ugc_ad_factory"}}
    result = forward(request, base_url="https://blaster.example", token="", opener=forbidden)
    assert result["error"]["code"] == -32001
    assert forward({"jsonrpc": "2.0", "method": "notifications/initialized"}, base_url="https://blaster.example", token="", opener=forbidden) is None


def test_backend_tool_error_is_preserved_instead_of_fabricating_success():
    expected = {"jsonrpc": "2.0", "id": "spend", "result": {"isError": True, "structuredContent": {"ok": False, "error": "human_approval_required"}}}
    result = forward(
        {"jsonrpc": "2.0", "id": "spend", "method": "tools/call", "params": {"name": "execute_ugc_ad_factory", "arguments": {"approved": False}}},
        base_url="https://blaster.example/api/mcp", token="test",
        opener=lambda *_args, **_kwargs: Response(json.dumps(expected).encode()),
    )
    assert result == expected


def test_http_auth_failure_never_echoes_token_or_response_body():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 401, "unauthorized secret-body", {}, io.BytesIO(b"secret-body"))

    result = forward({"jsonrpc": "2.0", "id": 3, "method": "tools/list"}, base_url="https://blaster.example", token="test-secret", opener=opener)
    assert result["error"]["code"] == -32004
    assert "test-secret" not in json.dumps(result)
    assert "secret-body" not in json.dumps(result)


def test_unreachable_api_returns_protocol_error():
    def opener(*_args, **_kwargs):
        raise URLError("no route")

    result = forward({"jsonrpc": "2.0", "id": 4, "method": "ping"}, base_url="https://blaster.example", token="test", opener=opener)
    assert result["error"]["code"] == -32005


def test_invalid_json_and_invalid_endpoint_fail_without_network():
    stdout = io.StringIO()
    serve(stdin=io.StringIO("not-json\n"), stdout=stdout, base_url="https://blaster.example", token="test")
    assert json.loads(stdout.getvalue())["error"]["code"] == -32700

    result = forward({"jsonrpc": "2.0", "id": 5, "method": "tools/list"}, base_url="file:///etc/passwd", token="test")
    assert result["error"]["code"] == -32002
