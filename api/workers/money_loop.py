"""Hourly money-loop synchronizer for the self-hosted backend."""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from ..services.performance_ingestion import sync_experiment


def _headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return {"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": "buffer_blaster"}


def _url(table: str) -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{table}"


async def active_experiments() -> list[dict[str, Any]]:
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY") and os.getenv("BUFFER_BLASTER_WORKSPACE_ID")):
        return []
    params = {
        "workspace_id": f"eq.{os.getenv('BUFFER_BLASTER_WORKSPACE_ID')}",
        "state": "in.(draft,active,testing,iterate)",
        "select": "id,state",
        "order": "created_at.asc",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("experiments"), params=params, headers=_headers())
    rows = response.json() if response.is_success else []
    return rows if isinstance(rows, list) else []


async def run_once() -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for experiment in await active_experiments():
        result = await sync_experiment(str(experiment["id"]))
        receipts.append({"experiment_id": experiment["id"], "ok": bool(result.get("ok")), "decision": result.get("decision")})
    return receipts


async def main() -> None:
    interval = max(300, int(os.getenv("MONEY_LOOP_SYNC_INTERVAL_SECONDS", "3600")))
    while True:
        try:
            receipts = await run_once()
            print({"worker": "money_loop", "experiments": len(receipts), "receipts": receipts}, flush=True)
        except Exception as exc:  # worker must survive one provider/API failure
            print({"worker": "money_loop", "error": type(exc).__name__}, flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
