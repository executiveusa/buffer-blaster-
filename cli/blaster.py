"""Command-line client for the Buffer Blaster API.

Examples:
  python -m cli.blaster status
  python -m cli.blaster pricing
  python -m cli.blaster campaign brief.json
  python -m cli.blaster ugc-plan brief.json
  python -m cli.blaster ugc-plan-create canonical-plan.json
  python -m cli.blaster ugc-plan-get <plan-id>
  python -m cli.blaster reference-analyze reference.json
  python -m cli.blaster reference-strategy <receipt-id>
  python -m cli.blaster ugc-execute approved-brief-with-wallet.json
  python -m cli.blaster wallet <wallet-id>
  python -m cli.blaster jobs
  python -m cli.blaster job <job-id>
  python -m cli.blaster accounts
  python -m cli.blaster schedule drop.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
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
        with urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode())
        except Exception:
            detail = {"error": exc.reason}
        return {"ok": False, "status": exc.code, "detail": detail}
    except Exception as exc:
        return {"ok": False, "error": "request_failed", "detail": type(exc).__name__}


def _help() -> None:
    print(
        "blaster <status|pricing|campaign|ugc-prompt|ugc-plan|ugc-plan-create|ugc-plan-get|reference-analyze|reference-strategy|ugc-execute|wallet|jobs|job|accounts|schedule|mcp-info> [json-file-or-id]"
    )


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in {"help", "--help", "-h"}:
        _help()
        return 0

    command = args[0]
    if command == "status":
        result = _call("/api/studio/status")
    elif command == "pricing":
        result = _call("/api/studio/pricing")
    elif command == "campaign" and len(args) > 1:
        result = _call("/api/studio/campaigns/plan", _load(args[1]))
    elif command == "ugc-prompt" and len(args) > 1:
        result = _call("/api/studio/ugc/prompt", _load(args[1]))
    elif command == "ugc-plan" and len(args) > 1:
        result = _call("/api/studio/ugc/factory/plan", _load(args[1]))
    elif command == "ugc-plan-create" and len(args) > 1:
        result = _call("/api/studio/ugc/plans", _load(args[1]))
    elif command == "ugc-plan-get" and len(args) > 1:
        result = _call(f"/api/studio/ugc/plans/{quote(args[1], safe='')}")
    elif command == "reference-analyze" and len(args) > 1:
        result = _call("/api/studio/reference-ads/analyze", _load(args[1]))
    elif command == "reference-strategy" and len(args) > 1:
        result = _call(f"/api/studio/reference-ads/strategy/{quote(args[1], safe='')}")
    elif command == "ugc-execute" and len(args) > 1:
        payload = _load(args[1])
        if payload.get("approved") is not True:
            result = {"ok": False, "error": "human_approval_required", "message": "ugc-execute JSON must include approved=true and a server-issued wallet_id."}
        elif not payload.get("wallet_id"):
            result = {"ok": False, "error": "wallet_id_required"}
        else:
            result = _call("/api/studio/ugc/factory/execute", payload)
    elif command == "wallet" and len(args) > 1:
        result = _call(f"/api/studio/billing/wallet/{quote(args[1], safe='')}")
    elif command == "jobs":
        result = _call("/api/studio/jobs")
    elif command == "job" and len(args) > 1:
        result = _call(f"/api/studio/jobs/{quote(args[1], safe='')}")
    elif command == "accounts":
        result = _call("/api/studio/social/accounts")
    elif command == "schedule" and len(args) > 1:
        payload = _load(args[1])
        if payload.get("approved") is not True:
            result = {"ok": False, "error": "human_approval_required", "message": "schedule JSON must include approved=true."}
        else:
            result = _call("/api/studio/social/schedule", payload)
    elif command == "mcp-info":
        result = {
            "ok": True,
            "product": "Buffer Blaster",
            "url": f"{BASE}/api/mcp",
            "transport": "http-json-rpc",
            "auth": "Bearer BLASTER_API_KEY",
            "paid_generation": "use execute_ugc_ad_factory with a server-owned wallet; no raw render bypass",
        }
    else:
        _help()
        print("Invalid command or missing JSON file / ID", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
