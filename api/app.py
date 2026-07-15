"""Stavarai Platform — FastAPI application factory.

Single-admin AI content-operations platform. Every `/api/admin/*` route is
guarded by a session token minted via `POST /api/auth/verify`.

Hot-path core (encryption, sessions, rate limiter, job queue) is supplied by
`api.services.native.get_core()` — which loads the prebuilt Rust lib if present
on this platform, else falls back to a pure-Python implementation of the same
contract. Either way the app runs with no compiler on the host.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    auth,
    blog,
    clients,
    content,
    dashboard,
    pipeline,
    settings as settings_router,
    voice,
)
from .services.native import backend_name

load_dotenv()

app = FastAPI(
    title="Stavarai Platform API",
    docs_url=None,        # disable Swagger in production
    redoc_url=None,
    openapi_url=None,
)

# ── CORS ───────────────────────────────────────────────────────
frontend_origin = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")
allowed = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    frontend_origin,
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Routers ────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(clients.router)
app.include_router(settings_router.router)
app.include_router(pipeline.router)
app.include_router(content.router)
app.include_router(blog.router)
app.include_router(voice.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "platform": os.getenv("PLATFORM_NAME", "Stavarai").lower(),
        "core": backend_name(),   # "rust" or "python"
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict:
    return {"name": "Stavarai Platform API", "health": "/api/health"}

