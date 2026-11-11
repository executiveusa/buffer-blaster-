from pathlib import Path

import asyncio
import hashlib
import json

import pytest

from api.services.ugc_executor import execute_ugc_factory_ad, extract_video_url, record_performance_review
from api.services.ugc_factory import UGCFactoryBrief


class FakeProvider:
    configured = True

    def __init__(self):
        self.calls = 0

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None, reference_image_urls=None, audio_url=None):
        return 80

    def status(self):
        return {"provider": "fake"}

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


class RecordingProvider(FakeProvider):
    def __init__(self):
        super().__init__()
        self.submit_calls = []
        self.estimate_calls = []

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None, reference_image_urls=None, audio_url=None):
        self.estimate_calls.append({"model_name": model_name, "image_url": image_url, "reference_image_urls": list(reference_image_urls or []), "audio_url": audio_url})
        return super().estimate_clip_cost_cents(model_name, image_url=image_url, reference_image_urls=reference_image_urls, audio_url=audio_url)

    async def submit_video(self, **kwargs):
        self.submit_calls.append(dict(kwargs))
        return await super().submit_video(**kwargs)


class ImagePricedProvider(RecordingProvider):
    """Text-to-video and image-to-video price differently, like a per-model provider."""

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None, reference_image_urls=None, audio_url=None):
        self.estimate_calls.append({"model_name": model_name, "image_url": image_url, "reference_image_urls": list(reference_image_urls or []), "audio_url": audio_url})
        return 50 if image_url else 30


class FakeStorage:
    def __init__(self):
        self.uploads = []

    async def download_url(self, url: str, destination: Path):
        destination.write_bytes(b"fake-video")
        return {"ok": True, "path": str(destination), "source_url": url}

    async def upload_file(self, source: Path, *, object_name: str, content_type: str, upsert: bool = True):
        self.uploads.append({"object_name": object_name, "upsert": upsert})
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


@pytest.fixture
def ledger(monkeypatch):
    """In-memory ledger double wired into the executor's module-level imports."""
    record = {}
    updates = []

    async def fake_create_job(**kwargs):
        record.clear()
        record.update({"id": "job-1", **kwargs})
        return dict(record)

    async def fake_update_job(job_id, **changes):
        record.update(changes)
        updates.append((job_id, changes))
        return dict(record)

    async def fake_get_job(job_id):
        # Deep copy: production backends serialize, so a caller's snapshot can
        # never mutate the stored record in place.
        return json.loads(json.dumps(record)) if record.get("id") == job_id else None

    async def fake_update_job_if(job_id, *, expected_state, expected_output=None, **changes):
        # Same CAS semantics as studio_ledger.update_job_if: no awaits between
        # the comparisons and the mutation, so check-and-set is atomic for
        # asyncio callers. The losing writer mutates nothing.
        if record.get("id") != job_id:
            return None
        if str(record.get("state") or "") != expected_state:
            return None
        if expected_output is not None and record.get("output") != expected_output:
            return None
        record.update(changes)
        updates.append((job_id, changes))
        return json.loads(json.dumps(record))

    monkeypatch.setattr("api.services.ugc_executor.create_job", fake_create_job)
    monkeypatch.setattr("api.services.ugc_executor.update_job", fake_update_job)
    monkeypatch.setattr("api.services.ugc_executor.update_job_if", fake_update_job_if)
    monkeypatch.setattr("api.services.ugc_executor.get_job", fake_get_job)
    return {"record": record, "updates": updates}


def _review(digest: str, **overrides):
    review = {
        "reviewer": "test-operator",
        "asset_sha256": digest,
        "checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": True},
    }
    review.update(overrides)
    return review


def test_extract_video_url_handles_common_provider_shapes():
    assert extract_video_url({"video": {"url": "https://cdn.example/a.mp4"}}) == "https://cdn.example/a.mp4"
    assert extract_video_url({"data": {"video": {"url": "https://cdn.example/b.mp4"}}}) == "https://cdn.example/b.mp4"
    assert extract_video_url({"output": {"video_url": "https://cdn.example/c.mp4"}}) == "https://cdn.example/c.mp4"


@pytest.mark.asyncio
async def test_executor_renders_two_clip_ad_and_waits_for_post_render_review(tmp_path, brief, ledger):
    storage = FakeStorage()
    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=FakeProvider(),
        storage=storage,
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )

    assert result["ok"] is False
    assert result["state"] == "needs_performance_review"
    assert result["job_id"] == "job-1"
    assert result["allowance"]["estimated_provider_cost_cents"] == 300
    assert result["allowance"]["ad_credits_required"] == 3
    assert result["allowance"]["remaining_provider_budget_after_cents"] == 100
    expected_prefix = hashlib.sha256(b"final").hexdigest()[:16]
    assert result["final_asset"]["signed_url"].endswith(f"final-{expected_prefix}.mp4")
    final_upload = [u for u in storage.uploads if "/final-" in u["object_name"]][0]
    assert final_upload["upsert"] is False
    expected_digest = hashlib.sha256(b"final").hexdigest()
    assert result["final_asset_sha256"] == expected_digest
    assert result["performance_review"] == {"required": True, "status": "pending"}
    assert ledger["record"]["output"]["final_asset_sha256"] == expected_digest
    assert any(change.get("state") == "needs_performance_review" for _, change in ledger["updates"])

    reviewed = await record_performance_review("job-1", _review(expected_digest))
    assert reviewed["ok"] is True
    assert reviewed["state"] == "finished"
    assert reviewed["approval_required_before_publish"] is True
    assert ledger["record"]["state"] == "finished"
    # The stored output keeps the asset and gains the review; nothing is clobbered.
    assert ledger["record"]["output"]["final_asset"]["signed_url"].endswith(f"final-{expected_prefix}.mp4")
    assert ledger["record"]["output"]["performance_review"]["checks"] == {
        "mouth_timing": True, "face": True, "hands": True, "continuity": True,
    }


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


@pytest.mark.asyncio
async def test_executor_feeds_casting_reference_to_clip_one_only(tmp_path, ledger):
    provider = RecordingProvider()
    casting_brief = UGCFactoryBrief(
        product="Cella Coffee",
        audience="home baristas",
        pain="getting inconsistent coffee every morning",
        mechanism="a measured roast and repeatable pour method",
        casting_reference_url="https://assets.example/creator.png",
    )

    result = await execute_ugc_factory_ad(
        casting_brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=provider,
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )
    assert result["state"] == "needs_performance_review"
    assert provider.submit_calls[0]["image_url"] == "https://assets.example/creator.png"
    assert provider.submit_calls[1]["image_url"] == "https://storage.example/jobs/job-1/seed.jpg"
    assert provider.estimate_calls[0]["image_url"] == "https://assets.example/creator.png"
    assert provider.estimate_calls[1]["image_url"] == "https://assets.example/creator.png"
    pricing = result["provider_pricing"]
    assert pricing["priced_with_image_input"] == {"clip_1": True, "clip_2": True, "seam_retry": True}


@pytest.mark.asyncio
async def test_executor_without_casting_reference_sends_no_image_for_clip_one(tmp_path, brief, ledger):
    provider = RecordingProvider()

    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=provider,
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )
    assert result["state"] == "needs_performance_review"
    assert provider.submit_calls[0]["image_url"] is None
    assert provider.estimate_calls[0]["image_url"] is None
    pricing = result["provider_pricing"]
    assert pricing["priced_with_image_input"] == {"clip_1": False, "clip_2": True, "seam_retry": True}


@pytest.mark.asyncio
async def test_executor_prices_each_call_at_its_actual_input_shape(tmp_path, brief, ledger):
    """Money: clip 2 and the seam retry always carry an image; never price all calls at the clip-1 rate."""
    provider = ImagePricedProvider()

    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=3,
        provider=provider,
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
    )
    pricing = result["provider_pricing"]
    assert pricing["clip_costs_cents"] == {"clip_1": 30, "clip_2": 50, "seam_retry": 50}
    # 30 + 2*50 = 130 raw, 12500 bps safety -> ceil(162.5) = 163.
    assert pricing["estimated_generation_cost_cents"] == 163


@pytest.mark.asyncio
async def test_executor_rejects_non_https_casting_reference_before_any_provider_call(tmp_path, monkeypatch):
    provider = RecordingProvider()
    bad_brief = UGCFactoryBrief(
        product="Cella Coffee",
        audience="home baristas",
        pain="getting inconsistent coffee every morning",
        mechanism="a measured roast and repeatable pour method",
        casting_reference_url="http://insecure.example/creator.png",
    )
    created = []

    async def fake_create_job(**kwargs):
        created.append(kwargs)
        return {"id": "job-x", **kwargs}

    monkeypatch.setattr("api.services.ugc_executor.create_job", fake_create_job)

    result = await execute_ugc_factory_ad(
        bad_brief,
        approved=True,
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
    assert result["error"] == "factory_gate_failed"
    assert provider.calls == 0
    assert provider.submit_calls == []
    assert provider.estimate_calls == []
    assert created == []


@pytest.mark.asyncio
async def test_performance_review_failed_check_marks_review_failed(tmp_path, brief, ledger):
    digest = hashlib.sha256(b"final").hexdigest()
    ledger["record"].update({"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}})

    reviewed = await record_performance_review("job-1", _review(digest, checks={"mouth_timing": True, "face": True, "hands": False, "continuity": True}))
    assert reviewed["ok"] is False
    assert reviewed["state"] == "performance_review_failed"
    assert reviewed["performance_review"]["checks"]["hands"] is False
    assert ledger["record"]["state"] == "performance_review_failed"


@pytest.mark.asyncio
async def test_performance_review_rejects_asset_digest_mismatch_without_state_change(tmp_path, brief, ledger):
    digest = hashlib.sha256(b"final").hexdigest()
    ledger["record"].update({"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}})

    reviewed = await record_performance_review("job-1", _review(hashlib.sha256(b"other").hexdigest()))
    assert reviewed["ok"] is False
    assert reviewed["error"] == "performance_review_asset_mismatch"
    assert ledger["record"]["state"] == "needs_performance_review"
    assert "performance_review" not in ledger["record"].get("output", {})


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", [
    {"checks": {}},
    {"checks": {"mouth_timing": True, "face": True, "hands": True}},
    {"checks": {"mouth_timing": True, "face": True, "hands": True, "continuity": "yes"}},
    {"reviewer": ""},
    {"asset_sha256": "not-a-digest"},
    {"evidence_urls": ["http://insecure.example/frame.png"]},
])
async def test_performance_review_rejects_blanket_or_malformed_attestations(tmp_path, ledger, mutation):
    digest = hashlib.sha256(b"final").hexdigest()
    ledger["record"].update({"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}})

    reviewed = await record_performance_review("job-1", _review(digest, **mutation))
    assert reviewed["ok"] is False
    assert reviewed["error"] == "performance_review_invalid"
    assert ledger["record"]["state"] == "needs_performance_review"


@pytest.mark.asyncio
async def test_concurrent_performance_reviews_exactly_one_wins_and_loser_mutates_nothing(ledger, monkeypatch):
    """Barrier-synced stale snapshots: the second review must conflict, never overwrite."""
    digest = hashlib.sha256(b"final").hexdigest()
    store = {"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}}
    both_read = asyncio.Event()
    reads = {"n": 0}

    async def racy_get_job(job_id):
        data = json.loads(json.dumps(store)) if store.get("id") == job_id else None
        reads["n"] += 1
        if reads["n"] >= 2:
            both_read.set()
        await both_read.wait()  # both reviewers now hold a stale pre-write snapshot
        return data

    async def cas_update_job_if(job_id, *, expected_state, expected_output=None, **changes):
        # Atomic check-and-set: no awaits between comparison and mutation.
        if store.get("id") != job_id or str(store.get("state") or "") != expected_state:
            return None
        if expected_output is not None and store.get("output") != expected_output:
            return None
        store.update(changes)
        return json.loads(json.dumps(store))

    monkeypatch.setattr("api.services.ugc_executor.get_job", racy_get_job)
    monkeypatch.setattr("api.services.ugc_executor.update_job_if", cas_update_job_if)

    approve = record_performance_review("job-1", _review(digest))
    reject = record_performance_review("job-1", _review(digest, checks={"mouth_timing": True, "face": True, "hands": False, "continuity": True}))
    results = await asyncio.gather(approve, reject)

    winners = [r for r in results if "error" not in r]
    losers = [r for r in results if r.get("error") == "performance_review_conflict"]
    assert len(winners) == 1, results
    assert len(losers) == 1, results
    # Exactly one review landed; the loser mutated nothing.
    assert store["state"] == winners[0]["state"]
    assert store["output"]["performance_review"]["passed"] is winners[0]["performance_review"]["passed"]
    assert losers[0]["ok"] is False


@pytest.mark.asyncio
async def test_performance_review_conflicts_when_asset_replaced_between_read_and_write(ledger, monkeypatch):
    """An asset/output change after the reviewer read the job must lose the CAS."""
    digest = hashlib.sha256(b"final").hexdigest()
    replaced = hashlib.sha256(b"replaced").hexdigest()
    store = {"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}}

    async def get_then_replace(job_id):
        data = json.loads(json.dumps(store))
        store["output"] = {"final_asset_sha256": replaced}  # concurrent asset replacement
        return data

    writes = {"n": 0}

    async def cas_update_job_if(job_id, *, expected_state, expected_output=None, **changes):
        writes["n"] += 1
        if store.get("id") != job_id or str(store.get("state") or "") != expected_state:
            return None
        if expected_output is not None and store.get("output") != expected_output:
            return None
        store.update(changes)
        return json.loads(json.dumps(store))

    monkeypatch.setattr("api.services.ugc_executor.get_job", get_then_replace)
    monkeypatch.setattr("api.services.ugc_executor.update_job_if", cas_update_job_if)

    result = await record_performance_review("job-1", _review(digest))
    assert result["ok"] is False
    assert result["error"] == "performance_review_conflict"
    assert writes["n"] == 1
    assert "performance_review" not in store["output"]  # loser mutated nothing
    assert store["state"] == "needs_performance_review"


@pytest.mark.asyncio
async def test_performance_review_is_labeled_human_attestation_not_independent_verification(ledger):
    digest = hashlib.sha256(b"final").hexdigest()
    ledger["record"].update({"id": "job-1", "state": "needs_performance_review", "output": {"final_asset_sha256": digest}})

    reviewed = await record_performance_review("job-1", _review(digest))
    record = reviewed["performance_review"]
    assert record["verification_basis"] == "human_attestation"
    assert record["independent_verification"] is False
    assert record["evidence_supplied"] is False
    stored = ledger["record"]["output"]["performance_review"]
    assert stored["verification_basis"] == "human_attestation"
    assert stored["independent_verification"] is False


@pytest.mark.asyncio
async def test_performance_review_requires_an_awaiting_job(tmp_path, ledger):
    digest = hashlib.sha256(b"final").hexdigest()

    missing = await record_performance_review("job-absent", _review(digest))
    assert missing["ok"] is False
    assert missing["error"] == "job_not_found"

    ledger["record"].update({"id": "job-1", "state": "finished", "output": {"final_asset_sha256": digest}})
    wrong_state = await record_performance_review("job-1", _review(digest))
    assert wrong_state["ok"] is False
    assert wrong_state["error"] == "job_not_awaiting_performance_review"


# ------------------------------------------- canonical durability gates


@pytest.mark.asyncio
@pytest.mark.parametrize("ledger_error", ["canonical_workspace_not_configured", "supabase_insert_failed", "redis_insert_failed", "canonical_ledger_unavailable"])
async def test_executor_never_calls_provider_when_canonical_write_fails(tmp_path, brief, ledger, monkeypatch, ledger_error):
    """Missing workspace or a failed insert leaves ledger_error on the create
    result; the executor must refuse BEFORE any provider call."""
    provider = RecordingProvider()

    async def failed_create_job(**kwargs):
        return {"id": "job-1", **kwargs, "ledger_error": ledger_error}

    monkeypatch.setattr("api.services.ugc_executor.create_job", failed_create_job)
    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
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
    assert result["error"] == "canonical_ledger_write_failed"
    assert result["state"] == "ledger_blocked"
    assert result["ledger_error"] == ledger_error
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_executor_never_calls_provider_when_canonical_readback_fails(tmp_path, brief, ledger, monkeypatch):
    """A create that cannot be read back is not durable; no paid work starts."""
    provider = RecordingProvider()

    async def no_readback(job_id):
        return None

    monkeypatch.setattr("api.services.ugc_executor.get_job", no_readback)
    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
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
    assert result["error"] == "canonical_ledger_readback_failed"
    assert result["state"] == "ledger_blocked"
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_executor_fails_closed_when_final_review_state_is_not_durable(tmp_path, brief, ledger, monkeypatch):
    """The final state write is verified by readback: if it is lost, the asset
    exists in storage but must NOT be deliverable or reviewable. The paid
    exposure evidence stays on the result so the caller refunds and records."""
    import api.services.ugc_executor as executor_mod

    provider = RecordingProvider()
    original_update = executor_mod.update_job

    async def lose_final_write(job_id, **changes):
        if changes.get("state") == "needs_performance_review":
            return None  # final write lost
        return await original_update(job_id, **changes)

    monkeypatch.setattr(executor_mod, "update_job", lose_final_write)
    result = await execute_ugc_factory_ad(
        brief,
        approved=True,
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
    assert result["state"] == "ledger_finalize_failed"
    assert result["error"] == "final_review_state_not_durable"
    assert result["customer_deliverable"] is False
    assert result["performance_review"] == {"required": True, "status": "blocked_ledger_not_durable"}
    # Evidence preserved: the stored asset and both paid-call receipts.
    assert result["final_asset"]["ok"] is True
    assert len(result["provider_receipts"]) == 2
    assert provider.calls == 2
    # The ledger never claims a reviewable state it could not persist.
    assert ledger["record"].get("state") != "needs_performance_review"


# ------------------- real Fal adapter, transport doubled at the httpx seam


class _FalErrorResponse:
    def __init__(self, status):
        self.is_error = True
        self.status_code = status
        self.text = "upstream error"

    def json(self):
        return {}


class _FalTransportClient:
    """Doubles only the httpx transport seam; the real adapter logic runs."""

    def __init__(self, calls, *, status=None, exc=None):
        self._calls = calls
        self._status = status
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, headers, json):
        self._calls.append({"url": url, "json": json})
        if self._exc is not None:
            raise self._exc
        return _FalErrorResponse(self._status)


def _real_fal_provider(monkeypatch, calls, *, status=None, exc=None, with_key=True):
    from api.services import media_generation

    if with_key:
        monkeypatch.setenv("FAL_KEY", "test-key")
    else:
        monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setenv("FAL_TEXT_VIDEO_MODEL", "configured/text-model")
    monkeypatch.setenv("FAL_IMAGE_VIDEO_MODEL", "configured/image-model")
    monkeypatch.delenv("FAL_AUDIO_INPUT_FIELD", raising=False)
    monkeypatch.delenv("FAL_IMAGE_INPUT_FIELD", raising=False)
    monkeypatch.setattr(
        media_generation.httpx, "AsyncClient",
        lambda *a, **k: _FalTransportClient(calls, status=status, exc=exc),
    )
    return media_generation.FalVideoProvider()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [500, 502])
async def test_real_fal_submit_5xx_after_send_settles_as_estimated_exposure_never_zero(tmp_path, brief, ledger, monkeypatch, status):
    """The REAL Fal adapter returns ok:false with a status AFTER client.post:
    the charge is unknown, never a definite zero."""
    from api.services.factory_runner import _settlement_cents

    calls = []
    provider = _real_fal_provider(monkeypatch, calls, status=status)
    sink = []
    result = await execute_ugc_factory_ad(
        brief, approved=True, offer_id="trial-7",
        remaining_provider_budget_cents=400, remaining_ad_credits=3,
        provider=provider, storage=FakeStorage(), media_ops=FakeMediaOps(),
        work_root=tmp_path, poll_interval_seconds=0, clip_receipts_sink=sink,
    )
    assert result["state"] == "clip_1_failed"
    assert len(calls) == 1  # the request really went out over the wire
    assert sink[0]["outcome"] == "uncertain_after_send"
    assert sink[0]["receipt"]["charge_outcome"] == "unknown_after_send"
    assert sink[0]["receipt"]["status"] == status
    assert sink[0]["estimated_cents"] == 80  # per-call estimate carried as the exposure basis
    split = _settlement_cents(sink, 80)
    assert split == {"definite_cents": 0, "uncertain_estimated_cents": 80, "rejected_calls": 0}


@pytest.mark.asyncio
async def test_real_fal_submit_transport_timeout_is_uncertain_after_send(tmp_path, brief, ledger, monkeypatch):
    calls = []
    provider = _real_fal_provider(monkeypatch, calls, exc=TimeoutError("read timeout"))
    sink = []
    result = await execute_ugc_factory_ad(
        brief, approved=True, offer_id="trial-7",
        remaining_provider_budget_cents=400, remaining_ad_credits=3,
        provider=provider, storage=FakeStorage(), media_ops=FakeMediaOps(),
        work_root=tmp_path, poll_interval_seconds=0, clip_receipts_sink=sink,
    )
    assert result["state"] == "clip_1_failed"
    assert len(calls) == 1  # send was attempted; outcome unknown
    assert sink[0]["outcome"] == "uncertain_after_send"


@pytest.mark.asyncio
async def test_real_fal_pre_send_config_validation_is_definitely_uncharged(tmp_path, brief, ledger, monkeypatch):
    """An invalid FAL_DURATION_TYPE fails local validation BEFORE any HTTP
    request: the call is definitely uncharged and settles at zero as a
    structured reject. (Missing FAL_KEY or a model override never reach this
    path: the executor's pricing preflight already blocks them.)"""
    from api.services.factory_runner import _settlement_cents

    calls = []
    monkeypatch.setenv("FAL_DURATION_TYPE", "bogus")  # read at adapter construction
    provider = _real_fal_provider(monkeypatch, calls)
    sink = []
    result = await execute_ugc_factory_ad(
        brief, approved=True, offer_id="trial-7",
        remaining_provider_budget_cents=400, remaining_ad_credits=3,
        provider=provider, storage=FakeStorage(), media_ops=FakeMediaOps(),
        work_root=tmp_path, poll_interval_seconds=0, clip_receipts_sink=sink,
    )
    assert result["state"] == "clip_1_failed"
    assert calls == []  # no HTTP request was ever made
    assert sink[0]["outcome"] == "rejected"
    assert sink[0]["receipt"]["charge_outcome"] == "not_sent"
    assert sink[0]["receipt"]["error"] == "invalid_fal_duration_type"
    split = _settlement_cents(sink, 80)
    assert split == {"definite_cents": 0, "uncertain_estimated_cents": 0, "rejected_calls": 1}
