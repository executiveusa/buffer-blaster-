"""Local one-shot render: price cap, real ffmpeg trim + end card, no key leakage."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from cli import render_local

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")

BRIEF = Path(__file__).resolve().parents[2] / "docs" / "examples" / "postatees-mariner-10s.json"


def _make_video(path: Path, seconds: int = 3) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=s=360x640:r=24:d={seconds}",
         "-f", "lavfi", "-i", f"sine=d={seconds}", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(path)],
        check=True,
    )


def _make_image(path: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=navy:s=360x640", "-frames:v", "1", str(path)], check=True)


class FakeFal:
    configured = True

    def __init__(self):
        self.submissions = []

    def status(self):
        return {"provider": "fal"}

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None):
        return 140

    async def submit_video(self, **kwargs):
        self.submissions.append(kwargs)
        return {"ok": True, "status_url": "https://queue.fal.run/s/1", "response_url": "https://queue.fal.run/r/1"}

    async def fetch_url(self, url):
        return {"ok": True, "data": {"status": "COMPLETED", "video": {"url": "https://v3.fal.media/files/clip.mp4"}}}


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    fake = FakeFal()
    monkeypatch.setattr(render_local, "get_media_provider", lambda: fake)
    clip = tmp_path / "provider-clip.mp4"
    _make_video(clip)

    async def fake_remote(self, url, destination):
        shutil.copyfile(clip, destination)
        return {"ok": True, "path": str(destination)}

    monkeypatch.setattr(render_local.AssetStorage, "download_url", fake_remote)
    return fake


def test_quote_prices_one_clip_before_any_key(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setenv("FAL_ESTIMATED_CLIP_COST_CENTS", "140")
    result = render_local.quote(render_local.load_brief(str(BRIEF)), with_first_frame=True)
    assert result["ok"] is True
    assert result["video_pricing"]["expected_paid_clip_calls"] == 1
    assert result["approve_cents_needed_for_render"] == 175


@pytest.mark.asyncio
async def test_render_refuses_when_approval_is_below_quote(tmp_path, fake_env):
    frame = tmp_path / "frame.png"
    _make_image(frame)
    brief = render_local.load_brief(str(BRIEF), product_reference_url=render_local.data_uri(frame))
    result = await render_local.render(brief, tmp_path / "final.mp4", approve_cents=100)
    assert result == {"ok": False, "error": "approval_below_quote", "quote_cents": 175, "approved_cents": 100}
    assert fake_env.submissions == []


@pytest.mark.asyncio
async def test_render_produces_final_with_end_card(tmp_path, fake_env, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "fal-secret-should-never-print")
    frame = tmp_path / "frame.png"
    mockup = tmp_path / "mockup.png"
    _make_image(frame)
    _make_image(mockup)
    brief = render_local.load_brief(
        str(BRIEF),
        product_reference_url=render_local.data_uri(frame),
        end_card_image_url=render_local.data_uri(mockup),
    )
    out = tmp_path / "out" / "final.mp4"
    result = await render_local.render(brief, out, approve_cents=175)

    assert result["ok"] is True, result
    assert result["qa"]["paid_generation_calls"] == 1
    assert result["qa"]["end_card"] is True
    assert len(fake_env.submissions) == 1
    assert fake_env.submissions[0]["image_url"].startswith("data:image/png;base64,")
    assert fake_env.submissions[0]["duration"] == "10"
    ops = render_local.get_media_ops()
    assert ops.has_audio(out)
    assert ops.duration_seconds(out) == pytest.approx(3 - 0.35 + 2, abs=0.25)
    assert "fal-secret" not in json.dumps(result, default=str)
    assert not list(out.parent.glob(".render-*"))


@pytest.mark.asyncio
async def test_keyframe_builds_mockup_request_and_respects_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "k")
    monkeypatch.setenv("FAL_KEYFRAME_MODEL", "fal-ai/nano-banana/edit")
    monkeypatch.setenv("FAL_KEYFRAME_COST_CENTS", "4")
    mockup = tmp_path / "mockup.png"
    _make_image(mockup)
    sent = {}

    async def fake_queue(model, body, *, timeout_seconds):
        sent.update(model=model, body=body)
        return {"ok": True, "data": {"images": [{"url": "data:image/png;base64," + render_local.data_uri(mockup).split(",", 1)[1]}]}}

    monkeypatch.setattr(render_local, "_fal_queue_run", fake_queue)
    brief = render_local.load_brief(str(BRIEF))

    blocked = await render_local.keyframe(brief, [mockup], tmp_path / "frame.png", approve_cents=3)
    assert blocked["error"] == "approval_below_quote" and not sent

    done = await render_local.keyframe(brief, [mockup], tmp_path / "frame.png", approve_cents=4)
    assert done["ok"] is True and (tmp_path / "frame.png").stat().st_size > 0
    assert sent["model"] == "fal-ai/nano-banana/edit"
    assert sent["body"]["aspect_ratio"] == "9:16"
    assert sent["body"]["image_urls"][0].startswith("data:image/png;base64,")
    assert "sleeve" in sent["body"]["prompt"] and "parked car" in sent["body"]["prompt"]
