from pathlib import Path

import pytest
from pydantic import ValidationError

from api.services import repurpose
from api.services.repurpose import RepurposePlanRequest, TranscriptSegment, build_repurpose_plan

ROOT = Path(__file__).resolve().parents[2]


def _request(**changes):
    payload = {
        "source_asset_key": "workspace/source/interview.mp4",
        "source_sha256": "a" * 64,
        "title": "Founder interview",
        "source_duration_seconds": 180,
        "transcript": [
            {"start_seconds": 5, "end_seconds": 18, "text": "Why most teams make this mistake before they launch, and how we fixed it."},
            {"start_seconds": 50, "end_seconds": 66, "text": "We tested the new workflow for 30 days because the old process wasted hours every week."},
            {"start_seconds": 120, "end_seconds": 136, "text": "Start with one step: check the source, prove the result, then use what actually worked."},
        ],
        "max_clips": 3,
        "target_clip_seconds": 30,
        "idempotency_key": "phase04-repurpose-001",
    }
    payload.update(changes)
    return RepurposePlanRequest(**payload)


def test_transcript_segment_and_source_bounds_fail_closed():
    with pytest.raises(ValidationError):
        TranscriptSegment(start_seconds=10, end_seconds=9, text="invalid")
    with pytest.raises(ValidationError):
        _request(
            source_duration_seconds=60,
            transcript=[{"start_seconds": 55, "end_seconds": 70, "text": "outside source"}],
        )


def test_plan_is_deterministic_ranked_and_no_spend():
    first = build_repurpose_plan(_request())
    second = build_repurpose_plan(_request())

    assert first == second
    assert first["clip_count"] == 3
    assert [clip["rank"] for clip in first["clips"]] == [1, 2, 3]
    assert first["clips"][0]["score"] >= first["clips"][1]["score"]
    assert first["paid_generation"] is False
    assert first["transcription_provider_called"] is False
    assert first["generation_provider_called"] is False
    assert first["approval_required_before_paid_render"] is True
    assert all(clip["crop_instruction"].startswith("vertical 9:16") for clip in first["clips"])


def test_overlapping_moments_are_diversified():
    request = _request(
        max_clips=3,
        transcript=[
            {"start_seconds": 10, "end_seconds": 20, "text": "Why this mistake changed everything and the proof surprised us."},
            {"start_seconds": 15, "end_seconds": 25, "text": "How this mistake changed everything with a measured result."},
            {"start_seconds": 100, "end_seconds": 112, "text": "The second lesson is how to use one clear step."},
        ],
    )
    plan = build_repurpose_plan(request)
    assert plan["clip_count"] == 2
    starts = [clip["start_seconds"] for clip in plan["clips"]]
    assert max(starts) - min(starts) > 50


@pytest.mark.asyncio
async def test_create_replays_same_plan_and_conflict_fails(monkeypatch):
    stored = {}

    async def fake_get(job_id):
        return stored.get(job_id)

    async def fake_create(**kwargs):
        record = {
            "id": kwargs["job_id"],
            "kind": kwargs["kind"],
            "state": kwargs["state"],
            "input": kwargs["input_payload"],
            "output": kwargs["output_payload"],
        }
        stored[record["id"]] = record
        return record

    monkeypatch.setattr(repurpose, "get_job", fake_get)
    monkeypatch.setattr(repurpose, "create_job", fake_create)

    first = await repurpose.create_repurpose_plan(_request())
    second = await repurpose.create_repurpose_plan(_request())
    assert first["ok"] is True and first["created"] is True
    assert second["ok"] is True and second["idempotent_replay"] is True
    assert first["plan"]["plan_id"] == second["plan"]["plan_id"]

    changed = await repurpose.create_repurpose_plan(_request(title="Different source title"))
    assert changed == {"ok": False, "error": "idempotency_conflict", "paid_generation": False}


def test_rest_mcp_cli_parity_and_no_provider_dependency():
    rest = (ROOT / "api/routers/repurpose.py").read_text(encoding="utf-8")
    mcp = (ROOT / "api/routers/mcp.py").read_text(encoding="utf-8")
    cli = (ROOT / "cli/blaster.py").read_text(encoding="utf-8")
    service = (ROOT / "api/services/repurpose.py").read_text(encoding="utf-8")

    assert '@router.post("/plans")' in rest
    assert '@router.get("/plans/{plan_id}")' in rest
    assert '"name": "create_repurpose_plan"' in mcp
    assert '"name": "get_repurpose_plan"' in mcp
    assert "repurpose-plan" in cli and "repurpose-get" in cli
    assert '"/api/studio/repurpose/plans"' in cli

    for forbidden in ["media_generation", "reserve_generation", "fal", "openai", "gemini", "whisper"]:
        assert forbidden not in service.lower()
    assert "estimated_provider_cost_cents=0" in service
