"""S7: captions - shared transcription + SRT/VTT + brand burn-in.

- transcribe(asset) returns word timestamps, cached by the asset's sha256 in
  Redis (bb:captions:{sha256}): the same file is never transcribed twice.
- The default backend is faster-whisper (self-hosted, pinned in
  requirements); it is imported lazily so the API runs without the model
  installed. Backends are injectable for tests.
- Caption layout: max 2 lines, <=42 chars per line, groups of <=5 words,
  bottom-safe for 9:16 (burn-in MarginV keeps text above the lower tenth).
- Burn-in uses the brand style (Inter, ink on lime-hued outline per Human
  Layer tokens) and writes a NEW asset; the original is never touched.
- Transcription is self-hosted: recorded in the usage ledger with
  provider-known actual_cents=0 (auditability, zero cap impact).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import redis.asyncio as redis

from . import source_assets, usage_ledger

MAX_LINE_CHARS = 42
MAX_LINES = 2
GROUP_WORDS = 5
#: Pinned self-hosted transcriber (manifest row: faster-whisper==1.2.1,
#: ctranslate2==4.9.0, model "base"; licenses MIT - docs/CAPTIONS.md).
#: The golden fixture proof (tests/golden/jfk_base_words.json) is generated
#: with exactly this version+model; accuracy beyond the proof is a model
#: choice, not a claim.
PINNED_WHISPER_MODEL = "base"
#: The runtime resolves exactly this HF snapshot revision (never a floating
#: "base" tag): the manifest pin is enforced at load, not just documented.
PINNED_MODEL_REPO = "Systran/faster-whisper-base"
PINNED_MODEL_REVISION = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
#: Pinned decoding parameters. Transcription must be deterministic across
#: runs and hosts, so no decode default is ever relied on: an unpinned
#: default + CPU thread scheduling once returned ZERO words for the golden
#: fixture (2/14 runs) and the pipeline silently accepted an empty
#: transcript. Beam, temperature, VAD, threading and drift control are all
#: explicit; changing any of them invalidates tests/golden/jfk_base_words.json.
DECODE_BEAM_SIZE = 5
DECODE_TEMPERATURE = 0.0
DECODE_VAD_FILTER = False
DECODE_CONDITION_ON_PREVIOUS_TEXT = False
MODEL_CPU_THREADS = 1
MODEL_NUM_WORKERS = 1
#: ctranslate2's int8 GEMM honors the math libraries' OWN threading, below
#: the WhisperModel(cpu_threads=1) pin: unpinned OMP/BLAS threads produced
#: divergent transcripts of the same fixture (2/10 runs). Pin every layer.
THREAD_ENV_PINS = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                   "MKL_NUM_THREADS": "1"}


def _pin_thread_env() -> None:
    import os
    for var, val in THREAD_ENV_PINS.items():
        os.environ[var] = val


_pin_thread_env()  # module import: before ctranslate2/OpenMP latch the env

#: One native model per process, created ONCE. Repeatedly constructing and
#: dropping ctranslate2 model objects corrupts decode intermittently
#: (observed: zero-word results and wrong-language garbage on later runs);
#: a process-resident instance is stable. The Redis busy lock already
#: serializes transcriptions per host, so a shared instance is never used
#: concurrently; the lock only guards creation against test-time races.
import threading as _threading

_MODEL_CACHE: dict[str, Any] = {}
_MODEL_CACHE_LOCK = _threading.Lock()


def _load_model(model_ref: str):
    from faster_whisper import WhisperModel
    with _MODEL_CACHE_LOCK:
        model = _MODEL_CACHE.get(model_ref)
        if model is None:
            model = WhisperModel(model_ref, device="cpu", compute_type="int8",
                                 cpu_threads=MODEL_CPU_THREADS,
                                 num_workers=MODEL_NUM_WORKERS)
            _MODEL_CACHE[model_ref] = model
    return model
#: Bounds: transcription is zero-FEE but not zero-cost (CPU/host). Files,
#: duration and concurrency are bounded; an unbounded agent transcribe is
#: a host-abuse vector.
MAX_AUDIO_SECONDS = int(os.getenv("CAPTIONS_MAX_SECONDS", "600"))
MAX_FILE_BYTES = int(os.getenv("CAPTIONS_MAX_BYTES", str(250 * 1024 * 1024)))
_BUSY_LOCK_TTL_MS = 15 * 60 * 1000


def _redis():
    return redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def _cache_key(sha256: str) -> str:
    return f"bb:captions:{sha256}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------- backend


class FasterWhisperBackend:
    """Self-hosted faster-whisper. Lazy import: the package and model are
    only needed when transcription actually runs."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("WHISPER_MODEL", PINNED_WHISPER_MODEL)

    async def transcribe(self, path: Path) -> dict[str, Any]:
        try:
            _pin_thread_env()  # before faster-whisper/ctranslate2 load
            from faster_whisper import WhisperModel
        except ImportError:
            return {"ok": False, "error": "backend_unavailable",
                    "detail": "faster-whisper is not installed in this environment"}
        import asyncio

        def _run() -> dict[str, Any]:
            model_ref: str = self.model_name
            if self.model_name == PINNED_WHISPER_MODEL:
                # enforce the pinned snapshot revision at runtime (cached
                # offline use falls back to local files only)
                from huggingface_hub import snapshot_download
                try:
                    model_ref = snapshot_download(PINNED_MODEL_REPO,
                                                  revision=PINNED_MODEL_REVISION)
                except Exception:
                    model_ref = snapshot_download(PINNED_MODEL_REPO,
                                                  revision=PINNED_MODEL_REVISION,
                                                  local_files_only=True)
            model = _load_model(model_ref)
            segments, info = model.transcribe(
                str(path), word_timestamps=True,
                beam_size=DECODE_BEAM_SIZE, temperature=DECODE_TEMPERATURE,
                vad_filter=DECODE_VAD_FILTER,
                condition_on_previous_text=DECODE_CONDITION_ON_PREVIOUS_TEXT)
            words = []
            for seg in segments:
                for w in (seg.words or []):
                    words.append({"start": round(float(w.start), 3),
                                  "end": round(float(w.end), 3),
                                  "text": w.word.strip()})
            return {"ok": True, "words": words, "language": info.language}

        return await asyncio.to_thread(_run)


# ---------------------------------------------------------------- formatting


def group_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group words into caption cues: <=GROUP_WORDS words, <=2 lines,
    <=42 chars/line. A word longer than the line limit gets its own line."""
    cues: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for word in words:
        candidate = current + [word]
        if len(candidate) > GROUP_WORDS or not _fits(candidate):
            if current:
                cues.append(_cue(current))
            current = [word]
        else:
            current = candidate
    if current:
        cues.append(_cue(current))
    return cues


def _wrap_lines(text: str) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for w in words:
        trial = f"{line} {w}".strip()
        if len(trial) <= MAX_LINE_CHARS:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines[:MAX_LINES]


def _fits(words: list[dict[str, Any]]) -> bool:
    return len(_wrap_lines(" ".join(w["text"] for w in words))) <= MAX_LINES


def _cue(words: list[dict[str, Any]]) -> dict[str, Any]:
    return {"start": words[0]["start"], "end": words[-1]["end"],
            "lines": _wrap_lines(" ".join(w["text"] for w in words)),
            "words": list(words)}


def _ts(seconds: float, sep: str = ",") -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def cues_to_srt(cues: list[dict[str, Any]]) -> str:
    out = []
    for i, cue in enumerate(cues, 1):
        out.append(f"{i}\n{_ts(cue['start'])} --> {_ts(cue['end'])}\n" + "\n".join(cue["lines"]) + "\n")
    return "\n".join(out)


def cues_to_vtt(cues: list[dict[str, Any]]) -> str:
    body = "\n\n".join(
        f"{_ts(cue['start'], '.')} --> {_ts(cue['end'], '.')}\n" + "\n".join(cue["lines"])
        for cue in cues)
    return f"WEBVTT\n\n{body}\n"


# ---------------------------------------------------------------- ASS burn

#: Brand burn style (docs/CAPTIONS.md): opaque ink box (#111111), white
#: inactive words, the ACTIVE word in lime (#B9FF66), Inter (fontconfig
#: fallback documented), MarginV=70 under the libass default PlayResY=288
#: scaling -> ~311px above the bottom of a 1280-tall frame: lower third,
#: above the platform-UI lower tenth. Pixel-verified in tests.
_ASS_HEADER = """[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Inter,14,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00111111,-1,0,0,0,100,100,0,0,3,6,0,2,40,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
_LIME_OVERRIDE = r"{\1c&H66FFB9&}"
_INK_RESET = r"{\1c&HFFFFFF&}"


def _ass_ts(seconds: float) -> str:
    cs = int(round(float(seconds) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s_, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s_:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return str(text).replace("{", "(").replace("}", ")")


def _wrap_word_lines(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    line: list[dict[str, Any]] = []
    for w in words:
        trial = " ".join(x["text"] for x in line + [w])
        if len(trial) <= MAX_LINE_CHARS:
            line.append(w)
        else:
            if line:
                lines.append(line)
            line = [w]
    if line:
        lines.append(line)
    return lines[:MAX_LINES]


def cues_to_ass(cues: list[dict[str, Any]]) -> str:
    """Karaoke-style burn: one Dialogue line per WORD interval; the active
    word renders lime on the opaque ink box, the rest white."""
    events: list[str] = []
    for cue in cues:
        lines = _wrap_word_lines(cue["words"])
        for active in cue["words"]:
            rendered = []
            for line in lines:
                parts = [(_LIME_OVERRIDE + _ass_escape(w["text"]) + _INK_RESET)
                         if w is active else _ass_escape(w["text"]) for w in line]
                rendered.append(" ".join(parts))
            events.append(
                f"Dialogue: 0,{_ass_ts(active['start'])},{_ass_ts(active['end'])},"
                "Caption,,0,0,0,," + r"\N".join(rendered))
    return _ASS_HEADER + "\n".join(events) + "\n"


# ---------------------------------------------------------------- service


def _duration_seconds(path: Path) -> float | None:
    if not shutil_which("ffprobe"):
        return None
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                          capture_output=True, timeout=60)
    try:
        return float(proc.stdout.decode().strip())
    except ValueError:
        return None


async def transcribe_asset(*, path: Path, asset_id: str | None = None,
                           actor: str = "api-key", backend: Any = None) -> dict[str, Any]:
    """Word timestamps for one asset, cached forever by content hash.
    Bounded: file size, audio duration, and one concurrent transcription
    per host (Redis lock) - zero-FEE is not zero host cost."""
    if not path.exists():
        return {"ok": False, "error": "asset_file_missing"}
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        return {"ok": False, "error": "asset_too_large", "max_bytes": MAX_FILE_BYTES}
    duration = _duration_seconds(path)
    if duration is None:
        return {"ok": False, "error": "ffprobe_unavailable",
                "detail": "OPERATOR: ffprobe is required for duration bounds; captions fail closed."}
    if duration > MAX_AUDIO_SECONDS:
        return {"ok": False, "error": "audio_too_long",
                "max_seconds": MAX_AUDIO_SECONDS, "duration": round(duration, 1)}
    digest = sha256_file(path)
    r = _redis()
    cached = await r.get(_cache_key(digest))
    if cached:
        result = json.loads(cached)
        result["cache_hit"] = True
        return result
    busy_token = f"{actor}:{uuid.uuid4()}"
    busy = await r.set("bb:captions:busy", busy_token, nx=True, px=_BUSY_LOCK_TTL_MS)
    if not busy:
        return {"ok": False, "error": "captions_busy",
                "detail": "Another transcription is running on this host; retry shortly."}
    try:
        backend = backend or FasterWhisperBackend()
        result = await backend.transcribe(path)
    finally:
        # fenced release: after a TTL lapse the lock may belong to a NEW
        # holder - only delete our own token, never theirs
        await r.eval("""if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
        return 0""", 1, "bb:captions:busy", busy_token)
    if not result.get("ok"):
        return result
    words = [w for w in result["words"] if w.get("text")]
    if not words:
        # fail closed: an empty transcript is NEVER a success. Caching it
        # would poison the content-hash cache with a silent no-speech
        # result and let a caption job report done with zero cues.
        return {"ok": False, "error": "empty_transcript",
                "detail": "Transcriber returned zero words; nothing is cached "
                          "and no captions are produced. Check the audio or retry."}
    cues = group_words(words)
    payload = {"ok": True, "sha256": digest, "asset_id": asset_id,
               "language": result.get("language"), "words": words, "cues": cues,
               "srt": cues_to_srt(cues), "vtt": cues_to_vtt(cues),
               "backend": type(backend).__name__, "model": getattr(backend, "model_name", None),
               "cache_hit": False}
    await r.set(_cache_key(digest), json.dumps(payload))
    await usage_ledger.record_usage(
        actor=actor, provider="faster-whisper",
        model=str(payload["model"] or PINNED_WHISPER_MODEL), kind="transcribe",
        job_id=asset_id, actual_cents=0)  # self-hosted: provider-known zero
    return payload


async def burn_captions(*, video_path: Path, words: list[dict[str, Any]],
                        actor: str = "api-key",
                        filename: str | None = None) -> dict[str, Any]:
    """Burn captions into a NEW asset with the brand style: opaque ink box,
    white inactive words, the ACTIVE word lime (one Dialogue per word
    interval). The original file is opened read-only and never modified."""
    if not shutil_which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg_not_available"}
    cues = group_words([w for w in words if w.get("text")])
    if not cues:
        return {"ok": False, "error": "no_speech_detected"}
    work = Path(tempfile.mkdtemp(prefix="bb-captions-"))
    ass_path = work / "captions.ass"
    ass_path.write_text(cues_to_ass(cues), encoding="utf-8")
    out_path = work / (Path(filename).stem + ".captioned.mp4" if filename else "captioned.mp4")
    # libass scales ASS margins by its default PlayResY (288): MarginV=70 ->
    # ~311px from the bottom of a 1280-tall 9:16 frame, the lower third,
    # above the platform-UI lower tenth (pixel-verified in tests; see
    # docs/CAPTIONS.md). When the host lacks Inter, fontconfig falls back
    # (DejaVu Sans on Linux) - the layout contract (2 lines / <=42 chars /
    # placement / ink box / lime active word) is font-independent.
    cmd = ["ffmpeg", "-y", "-i", str(video_path),
           "-vf", f"subtitles={ass_path}",
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "copy",
           str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, timeout=600)
    if proc.returncode != 0 or not out_path.exists():
        return {"ok": False, "error": "ffmpeg_failed",
                "detail": proc.stderr.decode("utf-8", "ignore")[-400:]}
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=format_name",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(out_path)],
                           capture_output=True, timeout=60)
    if probe.returncode != 0 or not probe.stdout.strip():
        return {"ok": False, "error": "ffprobe_rejected"}
    record = await source_assets.create_uploaded_reference(
        source=out_path, filename=out_path.name, content_type="video/mp4",
        metadata={"source": "captions_burn_in", "picked_by": actor,
                  "sha256": sha256_file(out_path),
                  "original_sha256": sha256_file(video_path)})
    if not record.get("ok"):
        return {"ok": False, "error": "asset_store_failed", "detail": record.get("error")}
    return {"ok": True, "asset": record.get("asset"),
            "output_sha256": sha256_file(out_path),
            "original_untouched": True, "ffprobe": "passed"}


def shutil_which(binary: str) -> bool:
    import shutil
    return shutil.which(binary) is not None


# ------------------------------------------------------- asset resolution


def _workspace_id() -> str:
    return os.getenv("STUDIO_WORKSPACE_ID", "").strip()


def _workspace_authorized(record: dict[str, Any]) -> bool:
    """Workspace authorization BEFORE any global sha256 cache lookup: an asset
    from another workspace is indistinguishable from missing, so a cached
    transcript can never leak across workspaces."""
    owner = record.get("workspace_id")
    if not owner:
        return False
    return owner == _workspace_id()


async def resolve_asset_to_temp(asset_id: str) -> dict[str, Any]:
    """Download one stored asset to a temp file (bounded by the storage
    adapter's max_download_bytes)."""
    import tempfile

    from . import source_assets
    from .asset_storage import get_asset_storage

    record = await source_assets.get_asset(asset_id)
    if not record or not _workspace_authorized(record):
        return {"ok": False, "error": "asset_not_found"}  # no cross-workspace signal
    url = record.get("signed_url") or record.get("storage_url")
    if not url:
        return {"ok": False, "error": "asset_has_no_file"}
    if record.get("storage_url") and not record.get("signed_url"):
        signed = await get_asset_storage().sign_path(str(record["storage_url"]))
        if not signed.get("ok"):
            return signed
        url = signed["signed_url"]
    filename = str((record.get("metadata") or {}).get("filename") or "asset.mp4")
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp4"
    dest = Path(tempfile.mkdtemp(prefix="bb-caption-src-")) / ("source" + suffix)
    downloaded = await get_asset_storage().download_url(str(url), dest)
    if not downloaded.get("ok"):
        return downloaded
    return {"ok": True, "path": dest, "record": record}


async def transcribe_by_asset_id(*, asset_id: str, actor: str = "api-key",
                                 backend: Any = None) -> dict[str, Any]:
    resolved = await resolve_asset_to_temp(asset_id)
    if not resolved.get("ok"):
        return resolved
    return await transcribe_asset(path=resolved["path"], asset_id=asset_id,
                                  actor=actor, backend=backend)


async def burn_by_asset_id(*, asset_id: str, actor: str = "api-key",
                           backend: Any = None) -> dict[str, Any]:
    """Transcribe (cache-reused) then burn; burned output is a new asset."""
    resolved = await resolve_asset_to_temp(asset_id)
    if not resolved.get("ok"):
        return resolved
    transcript = await transcribe_asset(path=resolved["path"], asset_id=asset_id,
                                        actor=actor, backend=backend)
    if not transcript.get("ok"):
        return transcript
    if not transcript.get("cues"):
        return {"ok": False, "error": "no_speech_detected"}
    filename = str((resolved["record"].get("metadata") or {}).get("filename") or "video.mp4")
    result = await burn_captions(video_path=resolved["path"], words=transcript["words"],
                                 actor=actor, filename=filename)
    if result.get("ok"):
        result["transcript"] = {"language": transcript.get("language"),
                                "cues": len(transcript["cues"]),
                                "cache_hit": transcript.get("cache_hit")}
    return result


async def get_captions(*, asset_id: str) -> dict[str, Any]:
    """Cached transcript for an asset (no recompute; no cache = not transcribed)."""
    from . import source_assets
    record = await source_assets.get_asset(asset_id)
    if not record or not _workspace_authorized(record):
        return {"ok": False, "error": "asset_not_found"}  # no cross-workspace signal
    digest = str((record.get("metadata") or {}).get("sha256") or "")
    if not digest:
        resolved = await resolve_asset_to_temp(asset_id)
        if not resolved.get("ok"):
            return resolved
        digest = sha256_file(resolved["path"])
    cached = await _redis().get(_cache_key(digest))
    if not cached:
        return {"ok": False, "error": "not_transcribed", "asset_id": asset_id}
    result = json.loads(cached)
    result["cache_hit"] = True
    return result
