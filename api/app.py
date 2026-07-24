"""Stavarai Platform / Buffer Blaster FastAPI application factory.

Private admin routes remain session-gated. Public creator discovery routes expose
only curated, provenance-aware creative cards and never private client data,
credentials, or internal orchestration details.

Hot-path core (encryption, sessions, rate limiter, job queue) is supplied by
`api.services.native.get_core()` — which loads the prebuilt Rust lib if present
on this platform, else falls back to a pure-Python implementation of the same
contract. Either way the app runs with no compiler on the host.
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
    pipeline,
    settings as settings_router,
    voice,
)
from .services.native import backend_name

load_dotenv()

app = FastAPI(
    title="Buffer Blaster API",
    docs_url=None,
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
app.include_router(discovery.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "platform": os.getenv("PLATFORM_NAME", "Buffer Blaster").lower(),
        "core": backend_name(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict:
    return {
        "name": os.getenv("PLATFORM_NAME", "Buffer Blaster API"),
        "health": "/api/health",
        "discover": "/v1/discover",
    }
