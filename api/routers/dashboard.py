"""Dashboard router — greets Stavarai by name, returns summary metrics.

Demo mode returns seeded metrics. Production queries Supabase.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import verify_session
from ..services import demo

router = APIRouter(prefix="/api/admin", tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(_=Depends(verify_session)) -> dict:
    clients = demo.list_clients()
    pending = demo.pending_approvals()
    return {
        "greeting": "Welcome back, Stavarai.",
        "active_clients": len(clients),
        "posts_this_week": demo.posts_this_week(),
        "pending_approvals": pending,
        "pipeline_running": demo.pipeline_running(),
        "clients": clients,
    }
