"""Stavarai Platform — FastAPI application factory.

Single-operator content-operations platform. Public publishing is always gated
by explicit human approval. UI, REST, MCP, CLI, plugin, and voice all resolve
to the same studio services.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    auth,
    blog,
    clients,
    content,
    dashboard,
    discovery,
    mcp,
    pipeline,
    settings as settings_router,
    studio,
    voice,
)
from .services.media_generation import get_media_provider
from .services.native import backend_name
from .services.publishing import get_publisher

load_dotenv()

app = FastAPI(
    title="Stavarai Platform API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

frontend_origin = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")
site_url = os.getenv("SITE_URL", "")
allowed = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    frontend_origin,
}
if site_url:
    allowed.add(site_url.rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in allowed if origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-api-key"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(clients.router)
app.include_router(settings_router.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(blog.router)
app.include_router(voice.router)
app.include_router(discovery.router)
app.include_router(studio.router)
app.include_router(mcp.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "platform": os.getenv("PLATFORM_NAME", "Stavarai").lower(),
        "core": backend_name(),
        "media_configured": get_media_provider().configured,
        "publisher_configured": get_publisher().configured,
        "approval_gate": True,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict:
    return {"name": "Stavarai Platform API", "health": "/api/health", "mcp": "/api/mcp"}
