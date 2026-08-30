"""End-to-end UGC factory execution coordinator.

This service bridges the deterministic factory plan to a final asset. Model IDs
remain environment-owned by the media provider. Public routes must reserve
provider spend from the server-owned wallet before invoking this coordinator.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .asset_storage import get_asset_storage
from .media_generation import get_media_provider
from .media_ops import get_media_ops
from .pricing import authorize_generation
from .studio_ledger import create_job, update_job
from .ugc_factory import UGCFactoryBrief, build_ugc_factory_plan


def extract_video_url(payload: Any) -> str | None:
    if isinstance(payload, str):
        return payload if payload.startswith("https://") and payload.lower().split("?", 1)[0].endswith((".mp4", ".mov", ".webm")) else None
    if isinstance(payload, list):
        for item in payload:
            found = extract_video_url(item)
            if found:
                return found
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("video_url", "url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith("https://"):
            if key == "video_url" or value.lower().split("?", 1)[0].endswith((".mp4", ".mov", ".webm")):
                return value
    for key in ("video", "output", "data", "result", "media", "files"):
        if key in payload:
            found = extract_video_url(payload[key])
            if found:
                return found
    for value in payload.values():
        if isinstance(value, (dict, list)):
            found = extract_video_url(value)
            if found:
                return found
    return None


def _provider_state(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    return str(payload.get("status") or payload.get("state") or payload.get("queue_status") or "").strip().lower()


async def _wait_for_video(provider: Any, receipt: dict[str, Any], *, poll_interval_seconds: float, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    status_url = str(receipt.get("status_url") or "")
    response_url = str(receipt.get("response_url") or "")
    last_payload: Any = None
    while time.monotonic() < deadline:
        url = status_url or response_url
        if not url:
            return {"ok": False, "error": "provider_receipt_missing_poll_url"}
        fetched = await provider.fetch_url(url)
        if not fetched.get("ok"):
            return {"ok": False, "error": "provider_poll_failed", "receipt": fetched}
        last_payload = fetched.get("data")
        direct = extract_video_url(last_payload)
        if direct:
            return {"ok": True, "video_url": direct, "provider_response": last_payload}
        state = _provider_state(last_payload)
        if state in {"failed", "error", "cancelled", "canceled"}:
            return {"ok": False, "error": "provider_generation_failed", "provider_response": last_payload}
        if state in {"completed", "complete", "succeeded", "success", "finished"} and response_url and response_url != url:
            fetched_response = await provider.fetch_url(response_url)
            if not fetched_response.get("ok"):
                return {"ok": False, "error": "provider_response_fetch_failed", "receipt": fetched_response}
            last_payload = fetched_response.get("data")
            direct = extract_video_url(last_payload)
            if direct:
                return {"ok": True, "video_url": direct, "provider_response": last_payload}
            return {"ok": False, "error": "provider_response_missing_video", "provider_response": last_payload}
        await asyncio.sleep(max(0.0, poll_interval_seconds))
    return {"ok": False, "error": "provider_generation_timeout", "provider_response": last_payload}


async def _submit_and_download(*, provider: Any, storage: Any, prompt: str, image_url: str | None, clip_number: int, workdir: Path, poll_interval_seconds: float, timeout_seconds: float) -> dict[str, Any]:
    receipt = await provider.submit_video(prompt=prompt, image_url=image_url, duration="10", aspect_ratio="9:16", generate_audio=True)
    if not receipt.get("ok"):
        return {"ok": False, "error": "provider_submit_failed", "clip": clip_number, "receipt": receipt}
    completed = await _wait_for_video(provider, receipt, poll_interval_seconds=poll_interval_seconds, timeout_seconds=timeout_seconds)
    if not completed.get("ok"):
        return {**completed, "clip": clip_number, "receipt": receipt}
    destination = workdir / f"clip-{clip_number}.mp4"
    downloaded = await storage.download_url(completed["video_url"], destination)
    if not downloaded.get("ok"):
        return {"ok": False, "error": "generated_video_download_failed", "clip": clip_number, "receipt": receipt, "download": downloaded}
    return {"ok": True, "clip": clip_number, "receipt": receipt, "provider_response": completed.get("provider_response"), "video_url": completed["video_url"], "local_path": destination}


def _valid_reserved_allowance(allowance: dict[str, Any] | None, *, expected_cost: int, offer_id: str) -> bool:
    return bool(
        allowance
        and allowance.get("ok") is True
        and allowance.get("wallet_id")
        and int(allowance.get("estimated_provider_cost_cents") or -1) == expected_cost
        and allowance.get("offer_id") in {None, offer_id}
    )


async def execute_ugc_factory_ad(
    brief: UGCFactoryBrief,
    *,
    approved: bool,
    offer_id: str,
    remaining_provider_budget_cents: int | None = None,
    remaining_ad_credits: int | None = None,
    reserved_allowance: dict[str, Any] | None = None,
    provider: Any | None = None,
    storage: Any | None = None,
    media_ops: Any | None = None,
    work_root: Path | None = None,
    poll_interval_seconds: float | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    plan = build_ugc_factory_plan(brief)
    if not plan.get("ok"):
        return {"ok": False, "error": "factory_gate_failed", "gate": plan.get("gate")}

    estimated_cost = int(plan.get("commercial", {}).get("estimated_generation_cost_cents") or 0)
    job = await create_job(
        kind="ugc_ad_factory",
        state="planned",
        input_payload={"brief": plan.get("brief"), "factory_version": plan.get("factory_version"), "approved": approved},
        estimated_provider_cost_cents=estimated_cost,
        offer_id=offer_id,
    )
    job_id = str(job.get("id") or "")
    if not job_id:
        return {"ok": False, "error": "ledger_job_creation_failed", "ledger": job}
    if not approved:
        return {"ok": False, "error": "human_approval_required", "approval_required": True, "state": "planned", "job_id": job_id}

    if reserved_allowance is not None:
        if not _valid_reserved_allowance(reserved_allowance, expected_cost=estimated_cost, offer_id=offer_id):
            await update_job(job_id, state="spend_blocked", output={"error": "invalid_spend_reservation"})
            return {"ok": False, "error": "invalid_spend_reservation", "state": "spend_blocked", "job_id": job_id}
        allowance = reserved_allowance
    else:
        # Internal/test compatibility only. Public routes do not accept balances.
        if remaining_provider_budget_cents is None or remaining_ad_credits is None:
            await update_job(job_id, state="spend_blocked", output={"error": "server_spend_reservation_required"})
            return {"ok": False, "error": "server_spend_reservation_required", "state": "spend_blocked", "job_id": job_id}
        allowance = authorize_generation(
            offer_id=offer_id,
            estimated_provider_cost_cents=estimated_cost,
            remaining_provider_budget_cents=remaining_provider_budget_cents,
            remaining_ad_credits=remaining_ad_credits,
        )
        if not allowance.get("ok"):
            await update_job(job_id, state="spend_blocked", output={"allowance": allowance})
            return {"ok": False, "error": allowance.get("error"), "state": "spend_blocked", "job_id": job_id, "allowance": allowance}

    provider = provider or get_media_provider()
    storage = storage or get_asset_storage()
    media_ops = media_ops or get_media_ops()
    if hasattr(storage, "configured") and not storage.configured:
        await update_job(job_id, state="storage_blocked", output={"error": "asset_storage_not_configured"})
        return {"ok": False, "error": "asset_storage_not_configured", "state": "storage_blocked", "job_id": job_id, "allowance": allowance}
    if hasattr(media_ops, "available") and not media_ops.available():
        await update_job(job_id, state="media_ops_blocked", output={"error": "ffmpeg_not_available"})
        return {"ok": False, "error": "ffmpeg_not_available", "state": "media_ops_blocked", "job_id": job_id, "allowance": allowance}

    root = work_root or Path(os.getenv("FACTORY_WORK_ROOT", "/tmp/buffer-blaster-factory"))
    workdir = root / job_id
    workdir.mkdir(parents=True, exist_ok=True)
    poll_interval = float(os.getenv("FAL_POLL_INTERVAL_SECONDS", "2")) if poll_interval_seconds is None else poll_interval_seconds
    timeout = float(os.getenv("FAL_RENDER_TIMEOUT_SECONDS", "600")) if timeout_seconds is None else timeout_seconds
    clip_receipts: list[dict[str, Any]] = []
    seam_threshold = float(plan.get("continuity", {}).get("seam_threshold_mean_abs_diff") or (5 / 255))

    try:
        await update_job(job_id, state="rendering_clip_1", output={"allowance": allowance})
        clip1 = await _submit_and_download(provider=provider, storage=storage, prompt=plan["clips"][0]["prompt"], image_url=None, clip_number=1, workdir=workdir, poll_interval_seconds=poll_interval, timeout_seconds=timeout)
        if not clip1.get("ok"):
            await update_job(job_id, state="clip_1_failed", provider_receipt={"clip_1": clip1})
            return {**clip1, "state": "clip_1_failed", "job_id": job_id, "allowance": allowance}
        clip_receipts.append({"clip": 1, "receipt": clip1.get("receipt"), "provider_response": clip1.get("provider_response")})

        clip1_trim = workdir / "clip-1-trim.mp4"
        trim1 = media_ops.trim_tail(clip1["local_path"], clip1_trim)
        if not trim1.get("ok"):
            await update_job(job_id, state="clip_1_trim_failed", output={"media_op": trim1})
            return {"ok": False, "error": trim1.get("error"), "state": "clip_1_trim_failed", "job_id": job_id, "allowance": allowance}
        seed = workdir / "seed.jpg"
        seed_result = media_ops.extract_last_frame(clip1_trim, seed)
        if not seed_result.get("ok"):
            await update_job(job_id, state="seed_extract_failed", output={"media_op": seed_result})
            return {"ok": False, "error": seed_result.get("error"), "state": "seed_extract_failed", "job_id": job_id, "allowance": allowance}
        seed_asset = await storage.upload_file(seed, object_name=f"jobs/{job_id}/seed.jpg", content_type="image/jpeg")
        if not seed_asset.get("ok") or not seed_asset.get("signed_url"):
            await update_job(job_id, state="seed_upload_failed", output={"storage": seed_asset})
            return {"ok": False, "error": seed_asset.get("error") or "seed_signed_url_missing", "state": "seed_upload_failed", "job_id": job_id, "allowance": allowance}

        async def render_second(attempt: int) -> dict[str, Any]:
            await update_job(job_id, state=f"rendering_clip_2_attempt_{attempt}")
            return await _submit_and_download(provider=provider, storage=storage, prompt=plan["clips"][1]["prompt"], image_url=seed_asset["signed_url"], clip_number=2, workdir=workdir, poll_interval_seconds=poll_interval, timeout_seconds=timeout)

        clip2 = await render_second(1)
        if not clip2.get("ok"):
            await update_job(job_id, state="clip_2_failed", provider_receipt={"clip_1": clip_receipts[0], "clip_2": clip2})
            return {**clip2, "state": "clip_2_failed", "job_id": job_id, "allowance": allowance}
        clip_receipts.append({"clip": 2, "attempt": 1, "receipt": clip2.get("receipt"), "provider_response": clip2.get("provider_response")})

        clip2_trim = workdir / "clip-2-trim.mp4"
        trim2 = media_ops.trim_tail(clip2["local_path"], clip2_trim)
        if not trim2.get("ok"):
            await update_job(job_id, state="clip_2_trim_failed", output={"media_op": trim2})
            return {"ok": False, "error": trim2.get("error"), "state": "clip_2_trim_failed", "job_id": job_id, "allowance": allowance}
        first2 = workdir / "clip-2-first.jpg"
        first2_result = media_ops.extract_first_frame(clip2_trim, first2)
        if not first2_result.get("ok"):
            await update_job(job_id, state="seam_frame_failed", output={"media_op": first2_result})
            return {"ok": False, "error": first2_result.get("error"), "state": "seam_frame_failed", "job_id": job_id, "allowance": allowance}
        seam = float(media_ops.seam_diff(seed, first2))

        if seam >= seam_threshold:
            clip2_retry = await render_second(2)
            if not clip2_retry.get("ok"):
                await update_job(job_id, state="seam_retry_failed", provider_receipt={"clips": clip_receipts, "retry": clip2_retry})
                return {**clip2_retry, "state": "seam_retry_failed", "job_id": job_id, "allowance": allowance}
            clip_receipts.append({"clip": 2, "attempt": 2, "receipt": clip2_retry.get("receipt"), "provider_response": clip2_retry.get("provider_response")})
            trim2 = media_ops.trim_tail(clip2_retry["local_path"], clip2_trim)
            first2_result = media_ops.extract_first_frame(clip2_trim, first2)
            if not trim2.get("ok") or not first2_result.get("ok"):
                await update_job(job_id, state="seam_retry_media_failed")
                return {"ok": False, "error": "seam_retry_media_failed", "state": "seam_retry_media_failed", "job_id": job_id, "allowance": allowance}
            seam = float(media_ops.seam_diff(seed, first2))
            if seam >= seam_threshold:
                await update_job(job_id, state="seam_qa_failed", output={"seam_diff": seam, "seam_threshold": seam_threshold})
                return {"ok": False, "error": "seam_qa_failed", "state": "seam_qa_failed", "job_id": job_id, "allowance": allowance, "seam_diff": seam, "seam_threshold": seam_threshold}

        await update_job(job_id, state="stitching", provider_receipt={"clips": clip_receipts})
        final_local = workdir / "final.mp4"
        stitched = media_ops.stitch(clip1_trim, clip2_trim, final_local)
        if not stitched.get("ok"):
            await update_job(job_id, state="stitch_failed", output={"media_op": stitched})
            return {"ok": False, "error": stitched.get("error"), "state": "stitch_failed", "job_id": job_id, "allowance": allowance}
        final_asset = await storage.upload_file(final_local, object_name=f"jobs/{job_id}/final.mp4", content_type="video/mp4")
        if not final_asset.get("ok"):
            await update_job(job_id, state="final_upload_failed", output={"storage": final_asset})
            return {"ok": False, "error": final_asset.get("error"), "state": "final_upload_failed", "job_id": job_id, "allowance": allowance}

        state = "finished" if stitched.get("audio") else "visual_complete_needs_audio"
        qa = {"seam_diff": seam, "seam_threshold": seam_threshold, "seam_passed": seam < seam_threshold, "audio_present_in_both_clips": bool(stitched.get("audio")), "paid_generation_calls": len(clip_receipts)}
        result = {"ok": state == "finished", "state": state, "job_id": job_id, "factory_version": plan.get("factory_version"), "allowance": allowance, "qa": qa, "final_asset": final_asset, "provider_receipts": clip_receipts, "approval_required_before_publish": True}
        await update_job(job_id, state=state, provider_receipt={"clips": clip_receipts}, output={"final_asset": final_asset, "qa": qa, "allowance": allowance})
        return result
    finally:
        if os.getenv("KEEP_FACTORY_WORKFILES", "false").lower() != "true":
            shutil.rmtree(workdir, ignore_errors=True)
