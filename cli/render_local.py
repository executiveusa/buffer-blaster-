"""One-shot local render for an operator, without Redis, Supabase or a running API.

Runs the same planner, gates and executor as the server, but keeps files on
local disk and keeps the job record in memory. Spend still needs an explicit
human cap: every paid command takes ``--approve-cents`` and refuses to start
when the quote is higher. The Fal key is read from the FAL_KEY environment
variable only and is never printed or written.

    python -m cli.render_local quote    BRIEF.json [--first-frame IMG]
    python -m cli.render_local keyframe BRIEF.json --reference IMG [--reference IMG] --out FRAME.png --approve-cents N
    python -m cli.render_local render   BRIEF.json --first-frame FRAME.png --out FINAL.mp4 --approve-cents N [--end-card-image IMG]

``keyframe`` turns product references (a flat mockup is fine) into a realistic
9:16 first frame using FAL_KEYFRAME_MODEL (an image-edit model such as
``fal-ai/nano-banana/edit``). Review that frame, then ``render`` animates it.
Image-to-video models start *on* the image they are given, so never feed a flat
mockup straight into ``render``.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from api.routers.studio import UGCFactoryPlanRequest
from api.services import ugc_executor
from api.services.asset_storage import AssetStorage
from api.services.media_generation import FalVideoProvider, get_media_provider
from api.services.media_ops import get_media_ops
from api.services.ugc_executor import estimate_factory_generation_cost, execute_ugc_factory_ad
from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan

MAX_INLINE_IMAGE_BYTES = 8 * 1024 * 1024


def data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) > MAX_INLINE_IMAGE_BYTES:
        raise SystemExit(f"{path.name} is larger than 8 MB; resize it first")
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    if not mime.startswith("image/"):
        raise SystemExit(f"{path.name} is not an image")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def load_brief(path: str, **overrides: Any) -> UGCFactoryBrief:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload.update({key: value for key, value in overrides.items() if value is not None})
    # Inline data URIs exceed the REST length limit, so validate them separately.
    long_fields = {key: payload.pop(key) for key in ("product_reference_url", "end_card_image_url") if key in payload}
    request = UGCFactoryPlanRequest(**payload)
    return UGCFactoryBrief(**{**request.model_dump(), **long_fields})


class LocalStorage:
    """Asset storage on local disk. Images 'uploaded' come back as data URIs so a
    provider can read them (e.g. the clip-2 seed frame) without a public bucket."""

    configured = True

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._remote = AssetStorage()

    async def download_url(self, url: str, destination: Path) -> dict[str, Any]:
        if url.startswith("data:"):
            try:
                header, encoded = url.split(",", 1)
                if ";base64" not in header:
                    return {"ok": False, "error": "unsupported_data_uri"}
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(base64.b64decode(encoded, validate=True))
            except (ValueError, base64.binascii.Error):
                return {"ok": False, "error": "invalid_data_uri"}
            return {"ok": True, "path": str(destination), "source_url": "data-uri"}
        return await self._remote.download_url(url, destination)

    async def upload_file(self, source: Path, *, object_name: str, content_type: str) -> dict[str, Any]:
        target = self.root / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        signed = data_uri(target) if content_type.startswith("image/") else target.resolve().as_uri()
        return {"ok": True, "path": str(target), "signed_url": signed, "backend": "local"}


_JOBS: dict[str, dict[str, Any]] = {}


async def _memory_create_job(**fields: Any) -> dict[str, Any]:
    record = {"id": f"local-{uuid.uuid4().hex[:12]}", **fields}
    _JOBS[record["id"]] = record
    return record


async def _memory_update_job(job_id: str, **changes: Any) -> dict[str, Any] | None:
    record = _JOBS.get(job_id)
    if record is None:
        return None
    record.update(changes)
    state = changes.get("state")
    if state:
        print(f"[{time.strftime('%H:%M:%S')}] {state}", file=sys.stderr)
    return record


def _keyframe_cost_cents() -> int:
    try:
        return max(0, int(os.getenv("FAL_KEYFRAME_COST_CENTS", "4")))
    except ValueError:
        return 4


def keyframe_prompt(brief: UGCFactoryBrief) -> str:
    parts = [
        "Photorealistic vertical 9:16 smartphone video still, first frame of a casual selfie video.",
        f"Subject: {brief.actor_description}.",
        f"Setting: {brief.setting}." if brief.setting else "",
        f"The subject wears the exact {brief.product} shown in the reference images: copy its colors, logos and graphics faithfully.",
        "Natural light, real skin texture, phone-camera look, subject framed chest-up and looking into the lens, mouth closed.",
        f"Avoid: {brief.avoid.rstrip('.')}." if brief.avoid else "",
        "No added text, captions or watermarks.",
    ]
    return " ".join(part for part in parts if part)


def quote(brief: UGCFactoryBrief, *, with_first_frame: bool) -> dict[str, Any]:
    if with_first_frame and not brief.product_reference_url:
        brief.product_reference_url = "data:image/png;base64,AA=="  # placeholder: price only
    plan = build_ugc_factory_plan(brief)
    provider = get_media_provider()
    model = str(plan.get("brief", {}).get("provider_model") or "").strip() or None
    pricing = estimate_factory_generation_cost(provider, plan, model) if provider.configured else {"ok": False, "error": "media_provider_not_configured"}
    if not pricing.get("ok") and isinstance(provider, FalVideoProvider):
        # Price from configuration even before a key is present.
        per_clip = int(os.getenv("FAL_ESTIMATED_CLIP_COST_CENTS", "150"))
        calls = int(plan.get("commercial", {}).get("expected_paid_clip_calls") or 1)
        safety = int(plan.get("commercial", {}).get("cost_safety_bps") or 10000)
        pricing = {
            "ok": True,
            "estimated_clip_cost_cents": per_clip,
            "expected_paid_clip_calls": calls,
            "estimated_generation_cost_cents": -(-per_clip * calls * safety // 10000),
            "note": "priced from FAL_ESTIMATED_CLIP_COST_CENTS; no FAL_KEY or model configured yet",
        }
    return {
        "gate": plan.get("gate"),
        "ok": plan.get("ok"),
        "clips": [{"clip": clip["clip"], "seconds": clip["duration_seconds"], "script": clip["script"]} for clip in plan.get("clips", [])],
        "video_pricing": pricing,
        "approve_cents_needed_for_render": pricing.get("estimated_generation_cost_cents"),
        "keyframe_cost_cents": _keyframe_cost_cents() if os.getenv("FAL_KEYFRAME_MODEL") else None,
        "end_card": plan.get("brief", {}).get("end_card_lines"),
    }


async def _fal_queue_run(model: str, body: dict[str, Any], *, timeout_seconds: float) -> dict[str, Any]:
    key = os.getenv("FAL_KEY", "")
    queue = os.getenv("FAL_QUEUE_URL", "https://queue.fal.run").rstrip("/")
    async with httpx.AsyncClient(timeout=60) as client:
        submitted = await client.post(f"{queue}/{model}", headers={"Authorization": f"Key {key}"}, json=body)
        if submitted.is_error:
            return {"ok": False, "error": "fal_submit_failed", "status": submitted.status_code, "detail": submitted.text[:500]}
        receipt = submitted.json()
    provider = FalVideoProvider()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = await provider.fetch_url(str(receipt.get("status_url") or ""))
        if not status.get("ok"):
            return {"ok": False, "error": "fal_poll_failed", "detail": status}
        state = str(status["data"].get("status") or "").upper()
        if state == "COMPLETED":
            result = await provider.fetch_url(str(receipt.get("response_url") or ""))
            return {"ok": result.get("ok", False), "data": result.get("data"), "request_id": receipt.get("request_id")}
        if state in {"FAILED", "ERROR", "CANCELLED"}:
            return {"ok": False, "error": "fal_generation_failed", "detail": status["data"]}
        await asyncio.sleep(2)
    return {"ok": False, "error": "fal_timeout", "request_id": receipt.get("request_id")}


def _first_image_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        images = payload.get("images")
        if isinstance(images, list) and images and isinstance(images[0], dict):
            url = images[0].get("url")
            return url if isinstance(url, str) else None
        image = payload.get("image")
        if isinstance(image, dict) and isinstance(image.get("url"), str):
            return image["url"]
    return None


async def keyframe(brief: UGCFactoryBrief, references: list[Path], out: Path, approve_cents: int) -> dict[str, Any]:
    model = os.getenv("FAL_KEYFRAME_MODEL", "").strip()
    if not os.getenv("FAL_KEY"):
        return {"ok": False, "error": "FAL_KEY_not_set"}
    if not model:
        return {"ok": False, "error": "FAL_KEYFRAME_MODEL_not_set"}
    cost = _keyframe_cost_cents()
    if approve_cents < cost:
        return {"ok": False, "error": "approval_below_quote", "quote_cents": cost, "approved_cents": approve_cents}
    body = {
        "prompt": keyframe_prompt(brief),
        os.getenv("FAL_KEYFRAME_IMAGE_FIELD", "image_urls"): [data_uri(path) for path in references],
        "num_images": 1,
        "aspect_ratio": "9:16",
        "output_format": "png",
    }
    result = await _fal_queue_run(model, body, timeout_seconds=300)
    if not result.get("ok"):
        return result
    url = _first_image_url(result.get("data"))
    if not url:
        return {"ok": False, "error": "keyframe_missing_image"}
    fetched = await LocalStorage(out.parent).download_url(url, out)
    return {"ok": bool(fetched.get("ok")), "keyframe": str(out), "request_id": result.get("request_id"), "approved_cents": approve_cents, "quote_cents": cost}


async def render(brief: UGCFactoryBrief, out: Path, approve_cents: int) -> dict[str, Any]:
    provider = get_media_provider()
    if not provider.configured:
        return {"ok": False, "error": "media_provider_not_configured", "hint": "set FAL_KEY and FAL_IMAGE_VIDEO_MODEL"}
    if not get_media_ops().available():
        return {"ok": False, "error": "ffmpeg_not_available"}
    plan = build_ugc_factory_plan(brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}
    model = str(plan.get("brief", {}).get("provider_model") or "").strip() or None
    pricing = estimate_factory_generation_cost(provider, plan, model)
    if not pricing.get("ok"):
        return pricing
    estimate = int(pricing["estimated_generation_cost_cents"])
    if approve_cents < estimate:
        return {"ok": False, "error": "approval_below_quote", "quote_cents": estimate, "approved_cents": approve_cents}

    original_ledger = (ugc_executor.create_job, ugc_executor.update_job)
    ugc_executor.create_job = _memory_create_job
    ugc_executor.update_job = _memory_update_job
    work = out.parent / f".render-{uuid.uuid4().hex[:8]}"
    storage = LocalStorage(work / "assets")
    allowance = {"ok": True, "wallet_id": "local-operator-cap", "offer_id": "local-operator", "estimated_provider_cost_cents": estimate, "approved_cap_cents": approve_cents}
    try:
        result = await execute_ugc_factory_ad(
            brief,
            approved=True,
            offer_id="local-operator",
            reserved_allowance=allowance,
            provider=provider,
            storage=storage,
            media_ops=get_media_ops(),
            work_root=work / "jobs",
        )
        final_path = (result.get("final_asset") or {}).get("path")
        if final_path:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(final_path, out)
            result["final_local_path"] = str(out)
        result.pop("allowance", None)
        result.get("final_asset", {}).pop("signed_url", None)
        return result
    finally:
        ugc_executor.create_job, ugc_executor.update_job = original_ledger
        shutil.rmtree(work, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cli.render_local", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("quote")
    q.add_argument("brief")
    q.add_argument("--first-frame", action="store_true", help="price the image-to-video model")
    k = sub.add_parser("keyframe")
    k.add_argument("brief")
    k.add_argument("--reference", action="append", required=True, type=Path)
    k.add_argument("--out", required=True, type=Path)
    k.add_argument("--approve-cents", required=True, type=int)
    r = sub.add_parser("render")
    r.add_argument("brief")
    r.add_argument("--first-frame", type=Path)
    r.add_argument("--end-card-image", type=Path)
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--approve-cents", required=True, type=int)
    args = parser.parse_args(argv)

    if args.command == "quote":
        result = quote(load_brief(args.brief), with_first_frame=args.first_frame)
    elif args.command == "keyframe":
        result = asyncio.run(keyframe(load_brief(args.brief), args.reference, args.out, args.approve_cents))
    else:
        overrides = {
            "product_reference_url": data_uri(args.first_frame) if args.first_frame else None,
            "end_card_image_url": data_uri(args.end_card_image) if args.end_card_image else None,
        }
        result = asyncio.run(render(load_brief(args.brief, **overrides), args.out, args.approve_cents))
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
