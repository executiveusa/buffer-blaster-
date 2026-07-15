"""Stavarai Platform — FastAPI backend.

Single-admin AI content-operations platform. Every `/api/admin/*` route is
guarded by a session token minted via `POST /api/auth/verify`.

Two operating modes:
  - Production: real Supabase + Rust core (when SUPABASE_URL is set).
  - Demo / dev: in-memory data when Supabase is not configured, so the
    platform boots with zero secrets for local development.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, dashboard, clients, settings as settings_router, \
    pipeline, content, blog, voice

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


# ── Session store (in-memory; Redis on VPS for multi-process) ──
SESSIONS: dict[str, float] = {}  # token -> expiry timestamp
SESSION_TTL = 86_400.0  # 24h


def issue_session() -> str:
    import secrets
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = time.time() + SESSION_TTL
    return token


def verify_session(request: Request) -> str:
    """Dependency: 401 unless a valid Bearer token is present."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = header.split(" ", 1)[1]
    expiry = SESSIONS.get(token)
    if not expiry or time.time() > expiry:
        SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return token


# ── Routers ────────────────────────────────────────────────────
app.include_router(auth.router)               # /api/auth/*
app.include_router(dashboard.router)          # /api/admin/dashboard
app.include_router(clients.router)            # /api/admin/clients*
app.include_router(settings_router.router)    # /api/admin/settings*
app.include_router(pipeline.router)           # /api/admin/pipeline*
app.include_router(content.router)            # /api/admin/content*
app.include_router(blog.router)               # /api/blog/*  (public) + admin
app.include_router(voice.router)              # /api/voice/*


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "platform": os.getenv("PLATFORM_NAME", "Stavarai").lower(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict:
    return {"name": "Stavarai Platform API", "health": "/api/health"}


def main() -> None:
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("API_RELOAD", "")),
    )


if __name__ == "__main__":
    main()
