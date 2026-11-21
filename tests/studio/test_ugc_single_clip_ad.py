"""Single-clip ads: operator scripts, real product reference, local end card."""
from pathlib import Path
import shutil
import subprocess

import pytest

from api.routers.mcp import _FACTORY_PROPERTIES
from api.services.media_ops import MediaOps
from api.services.ugc_executor import execute_ugc_factory_ad
from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from tests.studio.test_ugc_executor import FakeMediaOps, FakeProvider, FakeStorage

HOODIE_PHOTO = "https://cdn.example/hoodie-front.jpg"
CAR_LINE = (
    "Yo Mariner High, this one's for you. Postatees just dropped the Marauder hoodie "
    "and it's only seventy bucks."
)


def _single_brief(**overrides):
    values = {
        "product": "Postatees x Mariner High hoodie",
        "audience": "Mariner High students and families in Everett",
        "pain": "school gear that looks like everyone else's",
        "mechanism": "a one-run collab hoodie made with the school",
        "offer": "$70 pre-sale",
        "scripts": (CAR_LINE,),
        "clip_count": 1,
        "clip_duration_seconds": 10,
        "product_reference_url": HOODIE_PHOTO,
        "setting": "the front seat of a parked car, filmed on a phone on the dashboard",
        "pronunciation_notes": "Postatees is pronounced POH-stuh-teez.",
        "avoid": "close-ups of the sleeves or any sleeve lettering",
        "end_card_lines": ("Postatees x Mariner High", "$70 pre-sale"),
    }
    values.update(overrides)
    return UGCFactoryBrief(**values)


def test_single_clip_plan_uses_operator_script_reference_and_one_paid_call():
    plan = build_ugc_factory_plan(_single_brief())
    assert plan["ok"] is True, plan["gate"]
    assert len(plan["clips"]) == 1
    clip = plan["clips"][0]
    assert clip["script"] == CAR_LINE
    assert clip["reference_image_url"] == HOODIE_PHOTO
    assert "front seat of a parked car" in clip["prompt"]
    assert "POH-stuh-teez" in clip["prompt"]
    assert "sleeve lettering" in clip["prompt"]
    assert plan["commercial"]["expected_paid_clip_calls"] == 1
    assert plan["continuity"]["steps"] == ["generate_clip_1", "trim_clip_1_tail", "append_end_card"]
    assert plan["gate"]["checks"][0]["name"] == "single_clip_contract"


def test_default_two_clip_plan_is_unchanged():
    plan = build_ugc_factory_plan(
        UGCFactoryBrief(product="Cella Coffee", audience="home baristas", pain="flat coffee every morning", mechanism="a repeatable pour")
    )
    assert plan["ok"] is True
    assert len(plan["clips"]) == 2
    assert plan["gate"]["checks"][0]["name"] == "two_clip_contract"
    assert plan["clips"][0]["reference_image_url"] is None


def test_operator_script_still_passes_ad_tell_and_word_budget_gates():
    plan = build_ugc_factory_plan(_single_brief(scripts=("Buy now, link in bio.",)))
    assert plan["ok"] is False
    failed = {check["name"] for check in plan["gate"]["checks"] if not check["passed"]}
    assert failed == {"spoken_word_budget", "not_an_ad_mechanical_tells"}


def test_script_count_must_match_clip_count():
    plan = build_ugc_factory_plan(_single_brief(scripts=(CAR_LINE, CAR_LINE)))
    assert plan["ok"] is False
    assert plan["clips"] == []


def test_reference_must_be_https_and_clip_count_bounded():
    with pytest.raises(ValueError):
        build_ugc_factory_plan(_single_brief(product_reference_url="http://insecure.example/a.jpg"))
    with pytest.raises(ValueError):
        build_ugc_factory_plan(_single_brief(clip_count=3))


def test_mcp_schema_exposes_single_clip_fields():
    for field in ("scripts", "clip_count", "product_reference_url", "end_card_lines", "pronunciation_notes"):
        assert field in _FACTORY_PROPERTIES


class RecordingProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.submissions = []

    async def submit_video(self, **kwargs):
        self.submissions.append(kwargs)
        return await super().submit_video(**kwargs)


class EndCardMediaOps(FakeMediaOps):
    def __init__(self):
        self.end_cards = []

    def has_audio(self, source: Path):
        return True

    def append_end_card(self, source, destination, lines, *, seconds=2.0, background_image=None):
        self.end_cards.append({"lines": list(lines), "seconds": seconds, "background": background_image})
        destination.write_bytes(b"carded")
        return {"ok": True, "path": str(destination), "audio": True}


@pytest.mark.asyncio
async def test_executor_single_clip_renders_once_from_reference_and_adds_end_card(tmp_path, monkeypatch):
    async def fake_create_job(**kwargs):
        return {"id": "job-single", **kwargs}

    async def fake_update_job(job_id, **changes):
        return {"id": job_id, **changes}

    monkeypatch.setattr("api.services.ugc_executor.create_job", fake_create_job)
    monkeypatch.setattr("api.services.ugc_executor.update_job", fake_update_job)
    provider = RecordingProvider()
    media = EndCardMediaOps()

    result = await execute_ugc_factory_ad(
        _single_brief(),
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=provider,
        storage=FakeStorage(),
        media_ops=media,
        work_root=tmp_path,
        poll_interval_seconds=0,
    )

    assert result["ok"] is True, result
    assert result["state"] == "finished"
    assert provider.calls == 1
    assert provider.submissions[0]["image_url"] == HOODIE_PHOTO
    assert provider.submissions[0]["duration"] == "10"
    assert result["qa"]["paid_generation_calls"] == 1
    assert result["qa"]["end_card"] is True
    assert media.end_cards[0]["lines"] == ["Postatees x Mariner High", "$70 pre-sale"]
    assert media.end_cards[0]["background"] is not None
    assert result["allowance"]["estimated_provider_cost_cents"] == 100


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg not installed")
def test_media_ops_end_card_appends_seconds_and_keeps_audio(tmp_path):
    source = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=s=360x640:r=24:d=2",
            "-f", "lavfi", "-i", "sine=d=2",
            "-shortest", "-c:v", "libx264", "-c:a", "aac", str(source),
        ],
        check=True,
    )
    ops = MediaOps()
    out = tmp_path / "carded.mp4"
    result = ops.append_end_card(source, out, ["Postatees x Mariner", "$70"], seconds=1.5)
    assert result["ok"] is True, result
    assert ops.has_audio(out)
    assert ops.duration_seconds(out) == pytest.approx(3.5, abs=0.2)
    assert not list(tmp_path.glob("*endcard*.txt"))
