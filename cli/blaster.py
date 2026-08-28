"""Command-line client for the Agentic Social Studio API.

Examples:
  python -m cli.blaster status
  python -m cli.blaster campaign brief.json
  python -m cli.blaster ugc-prompt brief.json
  python -m cli.blaster accounts
  python -m cli.blaster schedule drop.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.getenv("BLASTER_API_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.getenv("BLASTER_API_KEY", "")


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _call(path: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(f"{BASE}{path}", data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode())
        except Exception:
            detail = {"error": exc.reason}
        return {"ok": False, "status": exc.code, "detail": detail}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in {"help", "--help", "-h"}:
        print("blaster <status|campaign|ugc-prompt|accounts|schedule|mcp-info> [json-file]")
        return 0
    command = args[0]
    if command == "status":
        result = _call("/api/studio/status")
    elif command == "campaign" and len(args) > 1:
        result = _call("/api/studio/campaigns/plan", _load(args[1]))
    elif command == "ugc-prompt" and len(args) > 1:
        result = _call("/api/studio/ugc/prompt", _load(args[1]))
    elif command == "accounts":
        result = _call("/api/studio/social/accounts")
    elif command == "schedule" and len(args) > 1:
        result = _call("/api/studio/social/schedule", _load(args[1]))
    elif command == "mcp-info":
        result = {"url": f"{BASE}/api/mcp", "transport": "http-json-rpc", "auth": "Bearer BLASTER_API_KEY"}
    else:
        print("Invalid command or missing JSON file", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
