"""S6: agent vision on footage - bounded, ledgered, schema-validated.

- Samples 1 frame per 2s, max 24 frames, 512px long edge (ffmpeg).
- Transcript context comes from the S7 captions cache (never recomputed
  here - no surprise host CPU).
- OpenRouter vision model from env (OPENROUTER_VISION_MODEL +
  OPENROUTER_API_KEY). Reasoning level resolves through S4 settings
  (model_settings.resolve_model_config, step="vision").
- Money: the model needs CONFIGURED vendor-grounded pricing
  (LLM_PRICE_OPENROUTER_{MODEL}_IN/OUT_CENTS_PER_MTOK) AND a configured
  vendor-grounded per-frame token count
  (VISION_TOKENS_PER_FRAME_{MODEL}) - both verified against the vendor's
  live docs by the operator (docs/VISION.md). Missing config REJECTS the
  run before any provider call; no invented 'conservative' number.
- Every provider call is ledgered (S4): byte-bound + frame-bound estimate
  held against owner caps BEFORE the call, exactly one usage row per call
  (kind='vision'), hold released after settle. A malformed model response
  is retried once, then fails; both calls are ledgered (they cost money)
  and the unused reservation settles back at the priced actual.
- Output schema is validated: scenes[{start,end,summary}],
  hook_candidates[{start,end,why}], product_visible[{start,end,confidence}],
  quality_flags[str], suggested_cuts[{start,end,reason?}]. Results are
  cached by content sha256 and linked to the plan.
- Tests inject the transport; no actual paid calls in the suite.
"""
from __future__ import annotations

import base64
import json
import math
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import redis.asyncio as redis

from . import captions, llm_adapter, model_settings, source_assets, usage_ledger

PROVIDER = "openrouter"


class UnsentProven(Exception):
    """Raised ONLY by our own transport wrapper when failure is provable
    before any byte was sent (httpx.ConnectError: connection never
    established). Any other exception - including arbitrary vendor/SDK
    flags - is treated as possibly-charged and ledgered conservatively."""
FRAME_INTERVAL_S = 2
MAX_FRAMES = 24
FRAME_LONG_EDGE = 512
MAX_SECONDS = int(os.getenv("VISION_MAX_SECONDS", "600"))
MAX_FILE_BYTES = int(os.getenv("VISION_MAX_BYTES", str(250 * 1024 * 1024)))
MAX_TOKENS_OUT = int(os.getenv("VISION_MAX_TOKENS_OUT", "2000"))
_BUSY_LOCK_TTL_MS = 15 * 60 * 1000

SCHEMA_VERSION = 1

SYSTEM_PROMPT = (
    "You analyze short vertical video footage for an ad-editing pipeline. "
    "Reply with ONLY one JSON object, no markdown, with exactly these keys: "
    "scenes: list of {start, end, summary}; "
    "hook_candidates: list of {start, end, why}; "
    "product_visible: list of {start, end, confidence} (0..1); "
    "quality_flags: list of short strings; "
    "suggested_cuts: list of {start, end, reason}. "
    "Times are seconds within the clip. Empty lists are fine."
)


def _redis() -> Any:
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def _cache_key(sha256: str) -> str:
    return f"bb:vision:{sha256}"


def _asset_key(asset_id: str) -> str:
    return f"bb:vision:asset:{asset_id}"


def _plan_key(plan_id: str) -> str:
    return f"bb:vision:plan:{plan_id}"


def vision_model() -> str | None:
    return os.getenv("OPENROUTER_VISION_MODEL") or None


def per_frame_tokens(model: str) -> int:
    """CONFIGURED vendor-grounded image tokens for one 512px frame of exactly
    this model, or raise. Source formula + URL + retrieval date live in
    docs/VISION.md; there is no default because image tokenization differs
    per model and an invented number is not a verifiable bound."""
    frag = llm_adapter._model_env_fragment(model)
    name = f"VISION_TOKENS_PER_FRAME_{frag}"
    raw = os.getenv(name, "")
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        raise llm_adapter.ModelPricingUnconfigured(PROVIDER, model, [name])


# ------------------------------------------------------------- frame sample


def _duration_seconds(path: Path) -> float | None:
    if not captions.shutil_which("ffprobe"):
        return None
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                          capture_output=True, timeout=60)
    try:
        return float(proc.stdout.decode().strip())
    except ValueError:
        return None


def extract_frames(path: Path, duration: float) -> dict[str, Any]:
    """1 frame per 2s, max MAX_FRAMES, 512px long edge, JPEG per frame.
    ffmpeg missing or unreadable video fails closed."""
    if not captions.shutil_which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg_unavailable",
                "detail": "OPERATOR: ffmpeg is required for frame sampling; vision fails closed."}
    count = max(1, min(MAX_FRAMES, int(duration // FRAME_INTERVAL_S)))
    work = Path(tempfile.mkdtemp(prefix="bb-vision-"))
    scale = f"scale='if(gt(iw,ih),{FRAME_LONG_EDGE},-2)':'if(gt(iw,ih),-2,{FRAME_LONG_EDGE})'"
    pattern = str(work / "frame-%03d.jpg")
    cmd = ["ffmpeg", "-y", "-i", str(path),
           "-vf", f"fps=1/{FRAME_INTERVAL_S},{scale}",
           "-frames:v", str(count), "-q:v", "5", pattern]
    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    frames = sorted(work.glob("frame-*.jpg"))
    if proc.returncode != 0 or not frames:
        return {"ok": False, "error": "frame_extract_failed",
                "detail": proc.stderr.decode("utf-8", "ignore")[-300:]}
    timed = [{"t": i * FRAME_INTERVAL_S, "path": f} for i, f in enumerate(frames)]
    return {"ok": True, "frames": timed, "count": len(timed)}


# ------------------------------------------------------------ schema check


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _check_span(item: Any, duration: float, keys: tuple[str, ...]) -> str | None:
    if not isinstance(item, dict):
        return "item not an object"
    start, end = item.get("start"), item.get("end")
    if not (_is_num(start) and _is_num(end)):
        return "start/end missing or non-numeric"
    if not (0 <= start <= end <= duration + FRAME_INTERVAL_S):
        return f"span {start}-{end} outside clip 0-{duration}"
    for key in keys:
        if not isinstance(item.get(key), str) or not item.get(key):
            return f"{key} missing or not a string"
    return None


def validate_analysis(obj: Any, duration: float) -> dict[str, Any]:
    """Strict shape check of the model output against the S6 schema."""
    if not isinstance(obj, dict):
        return {"ok": False, "error": "malformed_model_output", "detail": "top level not an object"}
    errors: list[str] = []
    for span in obj.get("scenes") if isinstance(obj.get("scenes"), list) else [None]:
        err = _check_span(span, duration, ("summary",))
        if err:
            errors.append(f"scenes: {err}")
    if not isinstance(obj.get("scenes"), list):
        errors.append("scenes: not a list")
    for hook in obj.get("hook_candidates") if isinstance(obj.get("hook_candidates"), list) else [None]:
        err = _check_span(hook, duration, ("why",))
        if err:
            errors.append(f"hook_candidates: {err}")
    if not isinstance(obj.get("hook_candidates"), list):
        errors.append("hook_candidates: not a list")
    pv = obj.get("product_visible")
    if not isinstance(pv, list):
        errors.append("product_visible: not a list")
    else:
        for item in pv:
            err = _check_span(item, duration, ())
            if err:
                errors.append(f"product_visible: {err}")
                continue
            conf = item.get("confidence")
            if not (_is_num(conf) and 0 <= conf <= 1):
                errors.append("product_visible: confidence missing or outside 0..1")
    qf = obj.get("quality_flags")
    if not isinstance(qf, list) or not all(isinstance(f, str) for f in qf):
        errors.append("quality_flags: not a list of strings")
    sc = obj.get("suggested_cuts")
    if not isinstance(sc, list):
        errors.append("suggested_cuts: not a list")
    else:
        for item in sc:
            err = _check_span(item, duration, ())
            if err:
                errors.append(f"suggested_cuts: {err}")
    if errors:
        return {"ok": False, "error": "malformed_model_output", "detail": "; ".join(errors[:5])}
    return {"ok": True, "analysis": {k: obj[k] for k in
            ("scenes", "hook_candidates", "product_visible", "quality_flags", "suggested_cuts")}}


def parse_model_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------- provider


def _build_prompt(*, frame_count: int, duration: float, transcript: str | None) -> str:
    parts = [
        f"Clip duration: {duration:.1f}s. {frame_count} frames follow, "
        f"one every {FRAME_INTERVAL_S}s; frame N (0-based) is at t=N*{FRAME_INTERVAL_S}s."
    ]
    if transcript:
        parts.append(f"Transcript: {transcript[:2000]}")
    parts.append("Return the JSON analysis object only.")
    return "\n".join(parts)


async def _openrouter_http(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Default transport: one OpenRouter chat completion. Tests inject their
    own transport; this is the only function that can spend money."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=payload)
    except httpx.ConnectError as exc:
        # connection never established: provably nothing was sent
        raise UnsentProven(str(exc)) from exc
    if resp.status_code >= 300:
        return {"ok": False, "error": "provider_error", "status": resp.status_code,
                "detail": resp.text[:300]}
    data = resp.json()
    choice = (data.get("choices") or [{}])[0]
    usage = data.get("usage") or {}
    return {"ok": True,
            "content": str((choice.get("message") or {}).get("content") or ""),
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "actual_cents": None}  # OpenRouter cost field is not assumed; priced from tokens


async def _call_model(*, model: str, key: str, prompt: str, frames: list[dict[str, Any]],
                      reasoning_level: str | None, transport: Any) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for frame in frames:
        b64 = base64.b64encode(Path(frame["path"]).read_bytes()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body: dict[str, Any] = {"model": model, "max_tokens": MAX_TOKENS_OUT,
                            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                         {"role": "user", "content": content}]}
    reasoning = (model_settings.reasoning_request_body(PROVIDER, reasoning_level)
                 if reasoning_level else None)
    if reasoning:
        body.update(reasoning)
    call = transport or _openrouter_http
    return await call(body, key)


# ---------------------------------------------------------------- service


async def analyze_footage(*, asset_id: str, plan_id: str | None = None,
                          actor: str = "api-key", transport: Any = None) -> dict[str, Any]:
    """Analyze one stored asset. Cached by content sha256; workspace
    authorization happens BEFORE any cache read (no cross-workspace leak)."""
    resolved = await captions.resolve_asset_to_temp(asset_id)
    if not resolved.get("ok"):
        return resolved
    path: Path = resolved["path"]
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        return {"ok": False, "error": "asset_too_large", "max_bytes": MAX_FILE_BYTES}
    digest = captions.sha256_file(path)
    r = _redis()
    cached = await r.get(_cache_key(digest))
    if cached:
        result = json.loads(cached)
        result["cache_hit"] = True
        if plan_id:
            await r.set(_plan_key(plan_id), digest)
        return result

    duration = _duration_seconds(path)
    if duration is None:
        return {"ok": False, "error": "ffprobe_unavailable",
                "detail": "OPERATOR: ffprobe is required for duration bounds; vision fails closed."}
    if duration > MAX_SECONDS:
        return {"ok": False, "error": "video_too_long",
                "max_seconds": MAX_SECONDS, "duration": round(duration, 1)}

    # --- pre-call configuration gates (no provider call before these pass)
    model = vision_model()
    if not model:
        return {"ok": False, "error": "model_not_configured",
                "detail": "Set OPENROUTER_VISION_MODEL to enable vision analysis."}
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"ok": False, "error": "provider_key_missing",
                "detail": "Set OPENROUTER_API_KEY to enable vision analysis."}
    try:
        pin, pout = llm_adapter.configured_prices(PROVIDER, model)
        frame_tokens = per_frame_tokens(model)
    except llm_adapter.ModelPricingUnconfigured as exc:
        return exc.detail

    sampled = extract_frames(path, duration)
    if not sampled.get("ok"):
        return sampled
    frames = sampled["frames"]

    transcript_text: str | None = None
    cap_cached = await r.get(captions._cache_key(digest))
    if cap_cached:
        words = (json.loads(cap_cached).get("words") or [])
        transcript_text = " ".join(w.get("text", "") for w in words) or None

    prompt = _build_prompt(frame_count=len(frames), duration=duration,
                           transcript=transcript_text)
    reasoning_level = None
    try:
        cfg = await model_settings.resolve_model_config(step="vision")
        if cfg.get("ok"):
            reasoning_level = cfg.get("reasoning_level")
    except Exception:
        reasoning_level = None  # no chat-model config: run without a reasoning param

    # --- proven upper bound: frames at the configured per-frame token count
    # + byte-bound text + full max_tokens output, at configured list price.
    est_in = len(frames) * frame_tokens + llm_adapter.estimate_input_tokens(prompt, SYSTEM_PROMPT)
    est = max(0, math.ceil((est_in * pin + MAX_TOKENS_OUT * pout) / 1_000_000))

    job_id = plan_id or asset_id
    busy_token = f"{actor}:{uuid.uuid4()}"
    busy = await r.set(f"bb:vision:busy:{digest}", busy_token, nx=True, px=_BUSY_LOCK_TTL_MS)
    if not busy:
        return {"ok": False, "error": "vision_busy",
                "detail": "This asset is already being analyzed; retry shortly."}

    analysis: dict[str, Any] | None = None
    last_error: dict[str, Any] | None = None
    try:
        for attempt in (1, 2):  # malformed output: retry once, then fail
            # F1: PER-ATTEMPT hold - one reservation covers exactly one paid
            # call; the retry gets a FRESH cap check (one shared hold for
            # two calls would overshoot the cap).
            hold_result = await usage_ledger.check_and_hold(job_id=job_id,
                                                            estimated_cents=est)
            if not hold_result.get("ok"):
                last_error = {"ok": False, "error": "usage_cap_exceeded",
                              "attempt": attempt, "hold": hold_result}
                break
            hold = hold_result.get("hold")
            try:
                call = await _call_model(model=model, key=key, prompt=prompt, frames=frames,
                                         reasoning_level=reasoning_level, transport=transport)
            except Exception as exc:
                # Unknown transport failure (timeout/disconnect AFTER send)
                # can still be charged: persist the conservative reservation
                # as a ledger row BEFORE releasing the hold - an invisible
                # refund would falsify the cap. The ONLY zero-cost path is
                # UnsentProven, raised by our own transport wrapper on proof
                # the request never went out.
                if not isinstance(exc, UnsentProven):
                    entry = await usage_ledger.record_usage(
                        actor=actor, provider=PROVIDER, model=model, kind="vision",
                        job_id=job_id, reasoning_level=reasoning_level,
                        estimated_cents=est)
                    if not entry.get("ok"):
                        # fail closed: keep the hold (reservation stays in
                        # cap totals) rather than dropping a paid call's cost
                        return {"ok": False, "error": "usage_ledger_write_failed",
                                "detail": entry.get("error"), "hold_kept": True,
                                "hold_id": (hold or {}).get("hold_id")}
                    await usage_ledger.release_hold(hold)
                    return {"ok": False, "error": "provider_transport_error",
                            "detail": type(exc).__name__, "ledgered": True}
                await usage_ledger.release_hold(hold)
                return {"ok": False, "error": "provider_transport_error",
                        "detail": type(exc).__name__, "ledgered": False,
                        "unsent_proven": True}
            # F2: ledger EVERY completed exchange BEFORE deciding anything.
            # A provider-error response is still a charged exchange: the
            # conservative reservation stays in cap totals
            # (cost_provenance='reservation_estimate', actual unknown) - an
            # invisible refund would falsify the cap.
            priced = None
            if call.get("ok") and call.get("tokens_in") is not None \
                    and call.get("tokens_out") is not None:
                priced = llm_adapter.priced_actual_cents(PROVIDER, model,
                                                         call["tokens_in"], call["tokens_out"])
            entry = await usage_ledger.record_usage(
                actor=actor, provider=PROVIDER, model=model, kind="vision",
                job_id=job_id, reasoning_level=reasoning_level,
                tokens_in=call.get("tokens_in") if call.get("ok") else None,
                tokens_out=call.get("tokens_out") if call.get("ok") else None,
                estimated_cents=est,
                actual_cents=call.get("actual_cents") if call.get("ok") else None,
                priced_actual_cents=priced,
                cost_provenance="computed_from_provider_tokens" if priced is not None else None)
            if not entry.get("ok"):
                # fail closed: a paid call whose cost row cannot be persisted
                # keeps its hold - the conservative reservation stays in cap
                # totals instead of refunding an invisible cost
                return {"ok": False, "error": "usage_ledger_write_failed",
                        "detail": entry.get("error"), "hold_kept": True,
                        "hold_id": (hold or {}).get("hold_id")}
            await usage_ledger.release_hold(hold)
            if not call.get("ok"):
                return call  # charged error is ledgered; no blind retry (no double spend)
            parsed = parse_model_json(call.get("content") or "")
            valid = validate_analysis(parsed, duration) if parsed is not None else \
                {"ok": False, "error": "malformed_model_output", "detail": "not JSON"}
            if valid.get("ok"):
                analysis = valid["analysis"]
                break
            last_error = valid
    finally:
        # fenced release: after a TTL lapse the lock may be a new holder's
        await r.eval("""if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
        return 0""", 1, f"bb:vision:busy:{digest}", busy_token)

    if analysis is None:
        return last_error or {"ok": False, "error": "malformed_model_output"}

    payload = {"ok": True, "schema_version": SCHEMA_VERSION, "sha256": digest,
               "asset_id": asset_id, "plan_id": plan_id, "model": model,
               "reasoning_level": reasoning_level, "frames_sampled": len(frames),
               "analysis": analysis, "cache_hit": False}
    await r.set(_cache_key(digest), json.dumps(payload))
    await r.set(_asset_key(asset_id), digest)
    if plan_id:
        await r.set(_plan_key(plan_id), digest)
    return payload


async def get_footage_analysis(*, asset_id: str) -> dict[str, Any]:
    """Cached analysis for an asset (no recompute)."""
    record = await source_assets.get_asset(asset_id)
    if not record or not captions._workspace_authorized(record):
        return {"ok": False, "error": "asset_not_found"}  # no cross-workspace signal
    r = _redis()
    digest = await r.get(_asset_key(asset_id))
    if not digest:
        return {"ok": False, "error": "not_analyzed", "asset_id": asset_id}
    cached = await r.get(_cache_key(str(digest)))
    if not cached:
        return {"ok": False, "error": "not_analyzed", "asset_id": asset_id}
    result = json.loads(cached)
    result["cache_hit"] = True
    return result
