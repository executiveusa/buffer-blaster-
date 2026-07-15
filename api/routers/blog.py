"""Blog router.

Public read of published posts (`GET /api/blog/posts`) + admin write endpoints.
Posts are stored as frontmatter+MDX on disk under `content/blog/` and read here
so the same source feeds the Next.js SSG and the API.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import verify_session

router = APIRouter(prefix="/api/blog", tags=["blog"])

_POSTS_DIR = Path(__file__).resolve().parents[2] / "content" / "blog"

_FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_frontmatter(body: str) -> tuple[dict[str, str], str]:
    m = _FM_RE.match(body)
    if not m:
        return {}, body
    fm_raw, content = m.group(1), m.group(2)
    meta: dict[str, str] = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, content


def _load_all() -> list[dict]:
    if not _POSTS_DIR.exists():
        return []
    posts = []
    for path in sorted(_POSTS_DIR.glob("*.mdx")):
        meta, _content = _parse_frontmatter(path.read_text(encoding="utf-8"))
        posts.append(
            {
                "slug": path.stem,
                "title": meta.get("title", path.stem),
                "excerpt": meta.get("excerpt", ""),
                "category": meta.get("category", "uncategorized"),
                "published_at": meta.get("date", ""),
                "reading_time": int(meta.get("reading_time", "5") or 5),
            }
        )
    posts.sort(key=lambda p: p["published_at"], reverse=True)
    return posts


@router.get("/posts")
async def list_posts() -> dict:
    return {"posts": _load_all()}


@router.get("/posts/{slug}")
async def get_post(slug: str) -> dict:
    path = _POSTS_DIR / f"{slug}.mdx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="post not found")
    meta, content = _parse_frontmatter(path.read_text(encoding="utf-8"))
    return {
        "slug": slug,
        "title": meta.get("title", slug),
        "excerpt": meta.get("excerpt", ""),
        "category": meta.get("category", "uncategorized"),
        "published_at": meta.get("date", ""),
        "reading_time": int(meta.get("reading_time", "5") or 5),
        "content": content,
    }


class PostDraft(BaseModel):
    title: str
    excerpt: Optional[str] = ""
    category: Optional[str] = "ai-content"
    content: str


@router.post("/posts")
async def create_draft(payload: PostDraft, _=Depends(verify_session)) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "-", payload.title.lower()).strip("-")
    path = _POSTS_DIR / f"{slug}.mdx"
    body = (
        "---\n"
        f'title: "{payload.title}"\n'
        f'excerpt: "{payload.excerpt}"\n'
        f"category: {payload.category}\n"
        f"date: {datetime.utcnow().date().isoformat()}\n"
        f"reading_time: 5\n"
        "---\n\n"
        f"{payload.content}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return {"slug": slug, "status": "draft", "message": "Draft saved."}
