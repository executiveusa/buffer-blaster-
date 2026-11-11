"""Build the ChatGPT GPT Action spec from the app's real OpenAPI.

Usage: python -m scripts.agent.build_chatgpt_action https://api.example.com > plugins/chatgpt/openapi.agent.json
Only the agent surface is exported; admin, billing activation, wallet
creation, token management and approval decisions are never included.
"""
from __future__ import annotations

import json
import sys
from typing import Any

AGENT_OPERATIONS: dict[tuple[str, str], str] = {
    ("get", "/api/agent/whoami"): "whoami",
    ("post", "/api/agent/approvals"): "requestApproval",
    ("get", "/api/agent/approvals"): "listApprovals",
    ("get", "/api/agent/approvals/{approval_id}"): "getApproval",
    ("get", "/api/studio/status"): "studioStatus",
    ("get", "/api/studio/pricing"): "getPricing",
    ("post", "/api/studio/ugc/factory/plan"): "createFactoryPlan",
    ("post", "/api/studio/ugc/factory/estimate"): "estimateFactory",
    ("post", "/api/studio/ugc/factory/execute"): "executeFactory",
    ("get", "/api/studio/jobs"): "listJobs",
    ("get", "/api/studio/jobs/{job_id}"): "getJob",
    ("get", "/api/studio/billing/wallet/{wallet_id}"): "getWallet",
    ("post", "/api/studio/social/schedule"): "scheduleSocialDrop",
}


def build(server_url: str) -> dict[str, Any]:
    from api.app import app

    full = app.openapi()
    paths: dict[str, Any] = {}
    for (method, path), op_id in AGENT_OPERATIONS.items():
        op = full["paths"][path][method]
        op = {**op, "operationId": op_id}
        op.pop("tags", None)
        paths.setdefault(path, {})[method] = op
    return {
        "openapi": "3.1.0",
        "info": {"title": "Buffer Blaster agent API", "version": full["info"].get("version", "1.0.0"),
                 "description": "Plan and price UGC ads freely. Rendering and publishing need a human-approved approval_id."},
        "servers": [{"url": server_url.rstrip("/")}],
        "paths": paths,
        "components": {
            "schemas": full.get("components", {}).get("schemas", {}),
            "securitySchemes": {"agentToken": {"type": "http", "scheme": "bearer"}},
        },
        "security": [{"agentToken": []}],
    }


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1] if len(sys.argv) > 1 else "https://YOUR-API-HOST"), indent=2))
