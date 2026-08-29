from pathlib import Path

import pytest

from api.services.ugc_executor import execute_ugc_factory_ad, extract_video_url
from api.services.ugc_factory import UGCFactoryBrief


class FakeProvider:
    def __init__(self):
        self.calls = 0

    async def submit_video(self, **kwargs):
        self.calls += 1
        return {
            "ok": True,
            "provider": "fal",
            "model": "fake/model",
            "request_id": f"req-{self.calls}",
            "response_url": f"https://queue.fal.run/response/{self.calls}",
            "status_url": f"https://queue.fal.run/status/{self.calls}",
        }

    async def fetch_url(self, url):
        clip = "clip2" if url.endswith("/2") else "clip1"
        return {
            "ok": True,
            "data": {
                "status": "COMPLETED",
                "video": {"url": f"https://cdn.example/{clip}.mp4"},
            },
        }


class FakeStorage:
    async def download_url(self, url: str, destination: Path):
        destination.write_bytes(b"fake-video")
        return {"ok": True, "path": str(destination), "source_url": url}

    async def upload_file(self, source: Path, *, object_name: str, content_type: str):
        return {
            "ok": True,
            "path": object_name,
            "signed_url": f"https://storage.example/{object_name}",
            "backend": "fake",
        }


class FakeMediaOps:
    def trim_tail(self, source: Path, destination: Path, seconds: float = 0.35):
        destination.write_bytes(b"trimmed")
        return {"ok": True, "path": str(destination)}

    def extract_last_frame(self, source: Path, destination: Path):
        destination.write_bytes(b"seed")
        return {"ok": True, "path": str(destination)}

    def extract_first_frame(self, source: Path, destination: Path):
        destination.write_bytes(b"first")
        return {"ok": True, "path": str(destination)}

    def seam_diff(self, left: Path, right: Path):
        return 0.01

    def stitch(self, first: Path, second: Path, destination: Path):
        destination.write_bytes(b"final")
        return {"ok": True, "path": str(destination), "audio": True}


@pytest.fixture
def brief():
    return UGCFactoryBrief(
        product="Cella Coffee",
        audience="home baristas",
        pain="getting inconsistent coffee every morning",
        mechanism="a measured roast and repeatable pour method",
        offer="POUR15",
    )


def test_extract_video_url_handles_common_provider_shapes():
    assert extract_video_url({"video": {"url": "https://cdn.example/a.mp4"}}) == "https://cdn.example/a.mp4"
    assert extract_video_url({"data": {"video": {"url": "https://cdn.example/b.mp4"}}}) == "https://cdn.example/b.mp4"
    assert extract_video_url({"output": {"video_url": "https://cdn.example/c.mp4"}}) == "https://cdn.example/c.mp4"


@pytest.mark.asyncio
async def test_executor_finishes_two_clip_ad_without_spend_in_test(tmp_path, monkeypatch, brief):
    async def fake_create_job(**kwargs):
        return {"id": "job-1", **kwargs}

    updates = []

    async def fake_update_job(job_id, **changes):
        updates.append((job_id, changes))
        return {"id": job_id, **changes}

    monkeypatch.setattr("api.services.ugc_executor.create_job", fake_create_job)
    monkeypatch.setattr("api.services.ugc_executor.update_job", fake_update_job)

    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=FakeProvider(),
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )

    assert result["ok"] is True
    assert result["state"] == "finished"
    assert result["job_id"] == "job-1"
    assert result["allowance"]["ad_credits_required"] == 3
    assert result["allowance"]["remaining_provider_budget_after_cents"] == 160
    assert result["final_asset"]["signed_url"].endswith("final.mp4")
    assert any(change.get("state") == "finished" for _, change in updates)


@pytest.mark.asyncio
async def test_executor_never_calls_provider_without_approval(tmp_path, monkeypatch, brief):
    provider = FakeProvider()

    async def fake_create_job(**kwargs):
        return {"id": "job-blocked", **kwargs}

    monkeypatch.setattr("api.services.ugc_executor.create_job", fake_create_job)

    result = await execute_ugc_factory_ad(
        brief,
        approved=False,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=provider,
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )
    assert result["ok"] is False
    assert result["error"] == "human_approval_required"
    assert provider.calls == 0
