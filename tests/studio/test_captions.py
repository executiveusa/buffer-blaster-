"""S7: captions - real pinned-transcriber golden proof, formatter contract,
cache, workspace authorization, host bounds, and pixel-verified burn-in.

The golden test runs the REAL pinned transcriber (faster-whisper==1.2.1,
ctranslate2==4.9.0, model 'base') on a committed public-domain speech
fixture (tests/fixtures/jfk.wav, JFK 'ask not' clip via the whisper.cpp
samples). A stub backend elsewhere proves only formatting; this test proves
actual transcription + timing stability (±150 ms golden tolerance).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import fakeredis
import pytest

from api.services import captions, source_assets, usage_ledger

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "jfk.wav"
GOLDEN = Path(__file__).resolve().parent.parent / "golden" / "jfk_base_words.json"


@pytest.fixture
def redis_fake(monkeypatch, tmp_path):
    fake = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(captions.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(source_assets.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(usage_ledger.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-test")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    return fake


WORDS = [
    {"start": 0.0, "end": 0.5, "text": "This"},
    {"start": 0.5, "end": 0.9, "text": "is"},
    {"start": 0.9, "end": 1.4, "text": "a"},
    {"start": 1.4, "end": 2.6, "text": "considerably"},
    {"start": 2.6, "end": 3.2, "text": "longer"},
    {"start": 3.2, "end": 4.0, "text": "caption"},
    {"start": 4.0, "end": 4.5, "text": "line"},
    {"start": 4.5, "end": 5.0, "text": "for"},
    {"start": 5.0, "end": 5.4, "text": "the"},
    {"start": 5.4, "end": 6.2, "text": "wrapping"},
    {"start": 6.2, "end": 6.9, "text": "rules"},
]


class StubBackend:
    model_name = "stub"

    def __init__(self):
        self.calls = 0

    async def transcribe(self, path):
        self.calls += 1
        return {"ok": True, "words": list(WORDS), "language": "en"}


def _clip(tmp_path: Path, seconds: float = 2.0) -> Path:
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=720x1280:d=" + str(seconds),
                    "-f", "lavfi", "-i", "sine=frequency=440:d=" + str(seconds),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(clip)],
                   capture_output=True, check=True, timeout=120)
    return clip


# ------------------------------------------------- real transcriber golden


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture missing")
@pytest.mark.asyncio
async def test_real_pinned_transcriber_golden(redis_fake):
    backend = captions.FasterWhisperBackend(captions.PINNED_WHISPER_MODEL)
    assert backend.model_name == "base", "pinned model drifted: re-run the golden"
    result = await captions.transcribe_asset(path=FIXTURE, backend=backend, actor="tester")
    assert result["ok"] is True and result["language"] == "en"
    text = " ".join(w["text"] for w in result["words"]).lower()
    assert "america" in text  # real speech recognized, not a stub
    golden = json.loads(GOLDEN.read_text())
    assert golden["model"] == captions.PINNED_WHISPER_MODEL
    assert golden["faster_whisper"] == "1.2.1"
    # timing stability: word count within ±1 and first/last word boundaries
    # within ±150ms of the committed golden
    assert abs(len(result["words"]) - len(golden["words"])) <= 1
    assert abs(result["words"][0]["start"] - golden["words"][0]["start"]) <= 0.150
    assert abs(result["words"][-1]["end"] - golden["words"][-1]["end"]) <= 0.150
    # ledgered at provider-known zero (self-hosted)
    events = await usage_ledger.list_events()
    assert events and events[0]["kind"] == "transcribe" and events[0]["actual_cents"] == 0


class EmptyBackend:
    model_name = "stub"

    async def transcribe(self, path):
        return {"ok": True, "words": [], "language": "en"}


@pytest.mark.asyncio
async def test_empty_transcript_fails_closed_never_cached(redis_fake, tmp_path):
    # Regression for the 2/14 golden flake: the transcriber returned ZERO
    # words and the pipeline accepted it as success. Empty is an ERROR,
    # never cached, never ledgered.
    clip = _clip(tmp_path)
    result = await captions.transcribe_asset(path=clip, backend=EmptyBackend(), actor="tester")
    assert result["ok"] is False and result["error"] == "empty_transcript"
    digest = captions.sha256_file(clip)
    assert await redis_fake.get(captions._cache_key(digest)) is None
    assert await usage_ledger.list_events() == []
    # the empty result did not stick: a later real backend transcribes fresh
    ok = await captions.transcribe_asset(path=clip, backend=StubBackend(), actor="tester")
    assert ok["ok"] is True and ok["words"]


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture missing")
@pytest.mark.asyncio
async def test_real_fixture_repeated_runs_never_empty_and_golden_stable(redis_fake):
    # Reviewer reproducer (2/14 flake: ok=True with ZERO words, silently
    # accepted): the REAL pinned transcriber on the REAL fixture, repeated.
    # Every run must (a) return words - empty is an error, never a success -
    # and (b) meet the committed golden bar: real speech recognized, word
    # count +/-1, first/last word boundaries within 150 ms. Token-level
    # punctuation can vary on CPU int8; the golden bar is the stability
    # contract, and the catastrophic modes (empty / wrong language / runaway
    # repetition) all violate it loudly.
    golden = json.loads(GOLDEN.read_text())
    for _ in range(5):
        backend = captions.FasterWhisperBackend(captions.PINNED_WHISPER_MODEL)
        res = await backend.transcribe(FIXTURE)
        assert res["ok"] is True and res["words"], "real transcriber returned zero words"
        words = res["words"]
        text = " ".join(w["text"] for w in words).lower()
        assert "america" in text
        assert abs(len(words) - len(golden["words"])) <= 1
        assert abs(words[0]["start"] - golden["words"][0]["start"]) <= 0.150
        assert abs(words[-1]["end"] - golden["words"][-1]["end"]) <= 0.150


# ------------------------------------------------------- formatter contract


def test_cues_respect_two_lines_and_42_chars():
    cues = captions.group_words(WORDS)
    for cue in cues:
        assert len(cue["lines"]) <= 2
        for line in cue["lines"]:
            assert len(line) <= 42


def test_srt_and_vtt_timings_stable():
    cues = captions.group_words(WORDS)
    srt = captions.cues_to_srt(cues)
    vtt = captions.cues_to_vtt(cues)
    assert "00:00:00,000 --> 00:00:03,200" in srt  # first cue boundary, exact ms
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:03.200" in vtt
    # no cue exceeds the line budget after wrapping
    for block in srt.strip().split("\n\n"):
        lines = block.splitlines()[2:]
        assert len(lines) <= 2 and all(len(l) <= 42 for l in lines)


# ------------------------------------------------------------- cache proof


@pytest.mark.asyncio
async def test_cache_hit_never_retranscribes(redis_fake, tmp_path):
    clip = _clip(tmp_path, 1.0)
    backend = StubBackend()
    first = await captions.transcribe_asset(path=clip, backend=backend, actor="t")
    assert first["ok"] is True and first["cache_hit"] is False
    second = await captions.transcribe_asset(path=clip, backend=backend, actor="t")
    assert second["cache_hit"] is True
    assert backend.calls == 1, "same content hash = no second transcription"


# ------------------------------------------------------------- host bounds


@pytest.mark.asyncio
async def test_duration_over_cap_rejected(redis_fake, tmp_path, monkeypatch):
    monkeypatch.setattr(captions, "MAX_AUDIO_SECONDS", 1)
    clip = _clip(tmp_path, 2.0)
    res = await captions.transcribe_asset(path=clip, backend=StubBackend())
    assert res["ok"] is False and res["error"] == "audio_too_long"


@pytest.mark.asyncio
async def test_concurrent_transcriptions_bounded(redis_fake, tmp_path):
    clip = _clip(tmp_path, 1.0)
    await redis_fake.set("bb:captions:busy", "someone-else", nx=True)
    res = await captions.transcribe_asset(path=clip, backend=StubBackend())
    assert res["ok"] is False and res["error"] == "captions_busy"


@pytest.mark.asyncio
async def test_missing_ffprobe_fails_closed(redis_fake, tmp_path, monkeypatch):
    monkeypatch.setattr(captions, "_duration_seconds", lambda p: None)
    clip = _clip(tmp_path, 1.0)
    res = await captions.transcribe_asset(path=clip, backend=StubBackend())
    assert res["ok"] is False and res["error"] == "ffprobe_unavailable"


# ---------------------------------------------------- workspace isolation


@pytest.mark.asyncio
async def test_cross_workspace_asset_is_invisible(redis_fake, monkeypatch):
    monkeypatch.setenv("STUDIO_WORKSPACE_ID", "ws-attacker")

    async def foreign_asset(asset_id):
        return {"id": asset_id, "workspace_id": "ws-victim",
                "storage_url": "victim/clip.mp4", "signed_url": None,
                "metadata": {"sha256": "abc"}}

    monkeypatch.setattr(source_assets, "get_asset", foreign_asset)
    res = await captions.get_captions(asset_id="a" * 32)
    assert res["ok"] is False and res["error"] == "asset_not_found"
    assert "cache" not in json.dumps(res), "no cache lookup before authorization"


# ------------------------------------------------------------ burn-in


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
@pytest.mark.asyncio
async def test_burn_writes_new_asset_original_untouched_and_pixels(redis_fake, tmp_path, monkeypatch):
    clip = _clip(tmp_path, 7.0)  # covers several word intervals for the highlight-move proof
    original_hash = captions.sha256_file(clip)

    class FakeStorage:
        configured = True

        async def upload_file(self, source, *, object_name, content_type):
            dest = tmp_path / ("stored-" + object_name.replace("/", "_"))
            shutil.copy(source, dest)
            return {"ok": True, "path": object_name, "signed_url": "https://signed.test/x"}

    monkeypatch.setattr(source_assets, "get_asset_storage", lambda: FakeStorage())
    backend = StubBackend()
    res = await captions.transcribe_asset(path=clip, backend=backend, actor="t")
    burn = await captions.burn_captions(video_path=clip, words=res["words"], actor="user:u1",
                                        filename="clip.mp4")
    assert burn["ok"] is True and burn["ffprobe"] == "passed"
    assert burn["original_untouched"] is True
    assert captions.sha256_file(clip) == original_hash, "original must be byte-identical"
    assert burn["output_sha256"] != original_hash
    assert burn["asset"]["metadata"]["source"] == "captions_burn_in"

    # PIXEL verification (not ffprobe alone): extract raw RGB of the same
    # frame from both videos; the bottom safe-area band must differ
    # (subtitles rendered there), the top band must be byte-identical.
    def band(path, ts, w, h, x, y):
        out = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", str(path), "-frames:v", "1",
             "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True, timeout=60)
        return out.stdout

    stored = tmp_path / "stored-captioned.mp4"
    if not stored.exists():
        stored = next(tmp_path.glob("stored-*.mp4"))
    # lower-third caption zone (MarginV=70 on PlayResY 288 -> ~311px up
    # from the bottom of the 1280-tall frame)
    safe_orig = band(clip, 0.5, 640, 180, 40, 830)
    safe_burn = band(stored, 0.5, 640, 180, 40, 830)
    top_orig = band(clip, 0.5, 720, 200, 0, 0)
    top_burn = band(stored, 0.5, 720, 200, 0, 0)
    assert safe_orig != safe_burn, "no caption pixels in the 9:16 lower-third safe band"
    bottom_orig = band(clip, 0.5, 720, 110, 0, 1170)
    bottom_burn = band(stored, 0.5, 720, 110, 0, 1170)
    assert bottom_orig == bottom_burn, "captions must stay out of the lower tenth (platform UI zone)"
    assert top_orig == top_burn, "burn-in must not alter frames outside the caption band"

    # BRAND STYLE pixel proof (not ffprobe, not prose): the caption band of
    # the burned frame must contain the opaque ink box AND the lime active
    # word, and the lime highlight must MOVE with the active word.
    def pixels(path, ts, w=640, h=180, x=40, y=830):
        raw = band(path, ts, w, h, x, y)
        return [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw) - 2, 3)]

    def near(px, target, tol=40):
        return all(abs(int(c) - t) <= tol for c, t in zip(px, target))

    def lime_center_x(path, ts):
        xs = [i % 640 for i, px in enumerate(pixels(path, ts)) if near(px, (0xB9, 0xFF, 0x66))]
        assert xs, f"no lime active-word pixels at t={ts}"
        return sum(xs) / len(xs)

    frame_t1 = pixels(stored, 0.25)  # active word: "This" (cue start)
    assert any(near(px, (0x11, 0x11, 0x11)) for px in frame_t1), "no opaque ink box pixels"
    x_first = lime_center_x(stored, 0.25)
    x_later = lime_center_x(stored, 1.0)  # active word: "a", later in the line
    assert x_later > x_first, f"lime highlight did not advance with the active word ({x_first} -> {x_later})"
