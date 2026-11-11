"""Slice 2: normalized identity reference-asset list across BOTH shots with the
continuity seed separate, a real audio-URL input distinct from the boolean
generate_audio flag, and model-specific capability fields (env-declared,
fail-closed - never env renames of the scalar/boolean fields).

Vendor contract grounding: fal minimax/h3-max reference-to-video + text-to-video
API contracts. These offline tests do not verify the live vendor contract.
No paid calls: the paid/external boundary is doubled, and the real Fal adapter
runs with only the httpx transport seam doubled.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.services.provider_contracts import UGCProviderJob
from api.services.ugc_executor import execute_ugc_factory_ad, estimate_factory_generation_cost
from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan

REFS = ["https://assets.example/creator-front.png", "https://assets.example/creator-smile.png"]


def _brief(**overrides) -> UGCFactoryBrief:
    base = {
        "product": "Cella Coffee",
        "audience": "home baristas",
        "pain": "getting inconsistent coffee every morning",
        "mechanism": "a measured roast and repeatable pour method",
        "offer": "POUR15",
    }
    base.update(overrides)
    return UGCFactoryBrief(**base)


# --------------------------------------------------------------- doubles


class RefProvider:
    """Provider double that accepts the reference-list contract."""

    configured = True

    def __init__(self):
        self.submit_calls = []
        self.estimate_calls = []

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None, reference_image_urls=None, audio_url=None):
        self.estimate_calls.append({"model_name": model_name, "image_url": image_url, "reference_image_urls": list(reference_image_urls or []), "audio_url": audio_url})
        return 80

    def status(self):
        return {"provider": "ref-fake"}

    async def submit_video(self, **kwargs):
        self.submit_calls.append(dict(kwargs))
        n = len(self.submit_calls)
        return {
            "ok": True,
            "provider": "fal",
            "model": "fake/model",
            "request_id": f"req-{n}",
            "response_url": f"https://queue.fal.run/response/{n}",
            "status_url": f"https://queue.fal.run/status/{n}",
        }

    async def fetch_url(self, url):
        clip = "clip2" if url.endswith("/2") else "clip1"
        return {"ok": True, "data": {"status": "COMPLETED", "video": {"url": f"https://cdn.example/{clip}.mp4"}}}


class LegacyProvider(RefProvider):
    """A provider whose estimate predates the reference-list capability."""

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None):
        return 80


class FakeStorage:
    configured = True

    async def download_url(self, url: str, destination: Path):
        destination.write_bytes(b"fake-video")
        return {"ok": True, "path": str(destination), "source_url": url}

    async def upload_file(self, source: Path, *, object_name: str, content_type: str, upsert: bool = True):
        return {"ok": True, "path": object_name, "signed_url": f"https://storage.example/{object_name}", "backend": "fake"}


class FakeMediaOps:
    def available(self):
        return True

    def trim_tail(self, source: Path, destination: Path):
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
        return json.loads(json.dumps(record)) if record.get("id") == job_id else None

    async def fake_update_job_if(job_id, *, expected_state, expected_output=None, **changes):
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


async def _execute(brief, provider, tmp_path, sink=None, ad_credits=3):
    return await execute_ugc_factory_ad(
        brief,
        approved=True,
        offer_id="trial-7",
        remaining_provider_budget_cents=400,
        remaining_ad_credits=ad_credits,
        provider=provider,
        storage=FakeStorage(),
        media_ops=FakeMediaOps(),
        work_root=tmp_path,
        poll_interval_seconds=0,
        clip_receipts_sink=sink,
    )


# --------------------------------------------------------------- plan level


def test_plan_carries_reference_list_on_both_clips_and_enforces_https():
    plan = build_ugc_factory_plan(_brief(casting_reference_urls=[REFS[0], f"  {REFS[1]}  ", ""]))
    assert plan["ok"], plan["gate"]
    # Normalized (trimmed, blanks dropped) and carried on the brief + BOTH clips.
    assert plan["brief"]["casting_reference_urls"] == REFS
    assert plan["clips"][0]["reference_image_urls"] == REFS
    assert plan["clips"][1]["reference_image_urls"] == REFS
    assert plan["casting"]["reference_list_applied_to"] == ["clip_1", "clip_2"]
    # The scalar clip-1 still is untouched by the list.
    assert plan["brief"]["casting_reference_url"] == ""

    bad = build_ugc_factory_plan(_brief(casting_reference_urls=["http://insecure.example/x.png"]))
    assert bad["ok"] is False
    check = next(c for c in bad["gate"]["checks"] if c["name"] == "casting_reference_urls_https")
    assert check["passed"] is False


def test_plan_clip_audio_gate_https_and_two_clip_bound():
    ok = build_ugc_factory_plan(_brief(clip_audio_urls=["https://audio.example/voice-1.mp3", "https://audio.example/voice-2.mp3"]))
    assert ok["ok"], ok["gate"]
    assert ok["clips"][0]["audio_url"] == "https://audio.example/voice-1.mp3"
    assert ok["clips"][1]["audio_url"] == "https://audio.example/voice-2.mp3"

    insecure = build_ugc_factory_plan(_brief(clip_audio_urls=["http://audio.example/voice.mp3"]))
    assert insecure["ok"] is False
    check = next(c for c in insecure["gate"]["checks"] if c["name"] == "clip_audio_urls_https")
    assert check["passed"] is False

    too_many = build_ugc_factory_plan(_brief(clip_audio_urls=[f"https://audio.example/{i}.mp3" for i in range(3)]))
    assert too_many["ok"] is False


# --------------------------------------------------------------- executor level


@pytest.mark.asyncio
async def test_executor_sends_reference_list_to_both_clips_seed_stays_separate(tmp_path, ledger):
    provider = RefProvider()
    result = await _execute(_brief(casting_reference_urls=REFS), provider, tmp_path)
    assert result["state"] == "needs_performance_review", result
    clip1, clip2 = provider.submit_calls
    # BOTH shots carry the identity reference list...
    assert clip1["reference_image_urls"] == REFS
    assert clip2["reference_image_urls"] == REFS
    # ...and the continuity seed on clip 2 is a SEPARATE start-frame input,
    # never folded into the reference list.
    assert clip1["image_url"] is None
    assert clip2["image_url"]
    assert clip2["image_url"] not in REFS
    # Pricing carried the reference shape for every paid call.
    assert result["provider_pricing"]["priced_with_reference_images"] == {"clip_1": True, "clip_2": True, "seam_retry": True}
    assert all(call["reference_image_urls"] == REFS for call in provider.estimate_calls)


@pytest.mark.asyncio
async def test_executor_clip_audio_urls_are_real_urls_distinct_from_the_boolean(tmp_path, ledger):
    provider = RefProvider()
    brief = _brief(clip_audio_urls=["https://audio.example/voice-1.mp3"])
    result = await _execute(brief, provider, tmp_path)
    assert result["state"] == "needs_performance_review", result
    clip1, clip2 = provider.submit_calls
    assert clip1["audio_url"] == "https://audio.example/voice-1.mp3"
    assert clip1["generate_audio"] is True  # the boolean flag is untouched by the URL
    assert "audio_url" not in clip2  # one URL supplied: clip 1 only


@pytest.mark.asyncio
async def test_pricing_fails_closed_when_provider_cannot_price_a_reference_list(tmp_path, ledger):
    """A provider whose estimate predates the capability returns no price, so
    the run blocks at preflight with ZERO provider calls - never a guessed rate."""
    provider = LegacyProvider()
    result = await _execute(_brief(casting_reference_urls=REFS), provider, tmp_path)
    assert result["ok"] is False
    assert result["state"] == "preflight_blocked"
    assert result["error"] == "provider_model_not_allowed_or_cost_unverified"
    assert provider.submit_calls == []


# ------------------------------------------- real Fal adapter, transport seam doubled


class _FalOkResponse:
    is_error = False
    status_code = 200
    text = ""

    def json(self):
        return {
            "request_id": "fal-req-1",
            "status_url": "https://queue.fal.run/status/1",
            "response_url": "https://queue.fal.run/result/1",
            "cancel_url": "https://queue.fal.run/cancel/1",
        }


class _FalCaptureClient:
    def __init__(self, calls, *args, **kwargs):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, headers, json):
        self.calls.append({"url": url, "json": json})
        return _FalOkResponse()


def _fal(monkeypatch, calls, **env):
    from api.services import media_generation

    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setenv("FAL_TEXT_VIDEO_MODEL", "fal-ai/minimax/h3-max/text-to-video")
    monkeypatch.setenv("FAL_IMAGE_VIDEO_MODEL", "fal-ai/minimax/h3-max/image-to-video")
    for name in ("FAL_REFERENCE_VIDEO_MODEL", "FAL_REFERENCE_IMAGES_FIELD", "FAL_AUDIO_URL_FIELD", "FAL_AUDIO_URL_MODELS", "FAL_AUDIO_INPUT_FIELD", "FAL_IMAGE_INPUT_FIELD", "FAL_PROMPT_EXPANSION_MODE"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        "api.services.media_generation.httpx.AsyncClient",
        lambda *args, **kwargs: _FalCaptureClient(calls, *args, **kwargs),
    )
    return media_generation.FalVideoProvider()


@pytest.mark.asyncio
async def test_fal_reference_list_fails_closed_when_capability_unconfigured(monkeypatch):
    calls = []
    provider = _fal(monkeypatch, calls)
    result = await provider.submit_video(prompt="hello", reference_image_urls=REFS)
    assert result["ok"] is False
    assert result["error"] == "fal_reference_images_not_configured"
    assert result["charge_outcome"] == "not_sent"
    assert set(result["missing"]) == {"FAL_REFERENCE_VIDEO_MODEL", "FAL_REFERENCE_IMAGES_FIELD", "FAL_PROMPT_EXPANSION_MODE"}
    assert calls == []  # fail-closed BEFORE any HTTP request
    # Pricing fails closed too: the capability cannot be priced unconfigured.
    assert provider.estimate_clip_cost_cents(reference_image_urls=REFS) is None


@pytest.mark.asyncio
async def test_fal_reference_list_uses_reference_model_and_list_field_seed_stays_scalar(monkeypatch):
    calls = []
    provider = _fal(
        monkeypatch, calls,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="reference_image_urls",
        FAL_IMAGE_INPUT_FIELD="image_url",
        FAL_PROMPT_EXPANSION_MODE="balanced",
    )
    # Clip-2 shape: identity list + SEPARATE continuity seed start frame.
    result = await provider.submit_video(
        prompt="clip 2", image_url="https://storage.example/jobs/job-1/seed.jpg",
        reference_image_urls=REFS, duration="10", aspect_ratio="9:16",
    )
    assert result["ok"] is True, result
    assert calls[0]["url"].endswith("fal-ai/minimax/h3-max/reference-to-video")
    body = calls[0]["json"]
    assert body["reference_image_urls"] == REFS
    assert body["image_url"] == "https://storage.example/jobs/job-1/seed.jpg"  # scalar seed, separate
    # Priced as the reference model.
    assert provider.estimate_clip_cost_cents(reference_image_urls=REFS) == 80
    assert "fal-ai/minimax/h3-max/reference-to-video" in provider.models()
    assert provider.capabilities().max_reference_images == 12


@pytest.mark.asyncio
async def test_fal_audio_url_fails_closed_unconfigured_and_stays_distinct_when_configured(monkeypatch):
    calls = []
    provider = _fal(monkeypatch, calls)
    refused = await provider.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3")
    assert refused["ok"] is False
    assert refused["error"] == "fal_audio_url_not_configured"
    assert refused["charge_outcome"] == "not_sent"
    assert calls == []

    calls2 = []
    configured = _fal(monkeypatch, calls2, FAL_AUDIO_URL_FIELD="target_audio_url", FAL_AUDIO_INPUT_FIELD="generate_audio", FAL_AUDIO_URL_MODELS="fal-ai/minimax/h3-max/text-to-video")
    ok = await configured.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3")
    assert ok["ok"] is True, ok
    body = calls2[0]["json"]
    assert body["target_audio_url"] == "https://audio.example/voice.mp3"  # the real audio URL...
    assert body["generate_audio"] is True  # ...distinct from the untouched boolean field


# --------------------------------------------------------------- gateway mirror


@pytest.mark.asyncio
async def test_gateway_fails_closed_on_unconfigured_reference_and_audio_fields(monkeypatch):
    from api.services.universal_media_gateway import UniversalVideoGatewayProvider

    monkeypatch.setenv("GENERATION_GATEWAY_BASE_URL", "https://gateway.example")
    monkeypatch.setenv("GENERATION_GATEWAY_API_KEY", "gw-key")
    monkeypatch.setenv("GENERATION_GATEWAY_TEXT_VIDEO_MODEL", "vendor/text-video")
    monkeypatch.delenv("GENERATION_GATEWAY_REFERENCE_IMAGES_FIELD", raising=False)
    monkeypatch.delenv("GENERATION_GATEWAY_AUDIO_URL_FIELD", raising=False)
    provider = UniversalVideoGatewayProvider()

    refs = await provider.submit_video(prompt="clip", reference_image_urls=REFS)
    assert refs["ok"] is False
    assert refs["error"] == "gateway_reference_images_not_configured"
    assert refs["charge_outcome"] == "not_sent"

    audio = await provider.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3")
    assert audio["ok"] is False
    assert audio["error"] == "gateway_audio_url_not_configured"
    assert audio["charge_outcome"] == "not_sent"

    assert provider.estimate_clip_cost_cents(reference_image_urls=REFS) is None


# --------------------------------------------------------------- contract lane


def test_provider_job_reference_and_audio_fields_validate_https():
    base = {
        "script": "word " * 20,
        "prompt": "a creator talking to camera",
        "idempotency_key": "job-key-0001",
        "estimated_cost_ceiling_cents": 500,
    }
    ok = UGCProviderJob(**base, reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3")
    assert ok.reference_image_urls == REFS

    with pytest.raises(Exception):
        UGCProviderJob(**base, reference_image_urls=["http://insecure.example/x.png"])
    with pytest.raises(Exception):
        UGCProviderJob(**base, audio_url="http://insecure.example/voice.mp3")
    with pytest.raises(Exception):
        UGCProviderJob(**base, reference_image_urls=[f"https://assets.example/{i}.png" for i in range(13)])


# ============================================================ R2 corrections


def test_public_estimate_matches_executor_pricing_for_reference_brief():
    """Regression for the observed 38c-public vs 375c-executor drift: the public
    preflight (REST /ugc/factory/estimate and MCP estimate_ugc_ad_factory both
    route through factory_runner.estimate_factory) must price the SAME full
    per-clip input contract the executor submits."""
    from dataclasses import asdict

    from api.services.factory_runner import estimate_factory

    provider = RefProvider()
    brief = _brief(casting_reference_urls=REFS, clip_audio_urls=["https://audio.example/voice-1.mp3", ""])
    public = estimate_factory(asdict(brief), provider=provider)
    assert public["ok"] is True, public
    plan = build_ugc_factory_plan(brief)
    direct = estimate_factory_generation_cost(
        provider, plan, None,
        image_url=None,
        reference_image_urls=REFS,
        clip_audio_urls=["https://audio.example/voice-1.mp3", ""],
    )
    assert direct["ok"] is True, direct
    assert public["estimated_generation_cost_cents"] == direct["estimated_generation_cost_cents"]
    assert public["pricing"]["priced_with_reference_images"] == {"clip_1": True, "clip_2": True, "seam_retry": True}
    assert public["pricing"]["priced_with_audio_urls"] == {"clip_1": True, "clip_2": False, "seam_retry": False}
    # MCP surface routes through the same function: identical result.
    from api.services.factory_runner import estimate_factory as mcp_estimate
    assert mcp_estimate(asdict(brief), provider=provider)["estimated_generation_cost_cents"] == direct["estimated_generation_cost_cents"]


def test_public_estimate_blocks_unsupported_reference_capability_early():
    from dataclasses import asdict

    from api.services.factory_runner import estimate_factory

    provider = LegacyProvider()  # estimate predates the reference contract
    public = estimate_factory(asdict(_brief(casting_reference_urls=REFS)), provider=provider)
    assert public["ok"] is False
    assert public["state"] == "preflight_blocked"
    assert public["error"] == "provider_model_not_allowed_or_cost_unverified"
    assert provider.submit_calls == []


def test_clip_audio_slots_never_shift_and_malformed_entries_fail():
    # A blank slot means "no pinned voice for THIS clip" - clip 2's URL must
    # never shift onto clip 1.
    plan = build_ugc_factory_plan(_brief(clip_audio_urls=["", "  https://audio.example/clip2.wav  "]))
    assert plan["ok"], plan["gate"]
    assert plan["clips"][0]["audio_url"] is None
    assert plan["clips"][1]["audio_url"] == "https://audio.example/clip2.wav"
    assert plan["brief"]["clip_audio_urls"] == ["", "https://audio.example/clip2.wav"]

    malformed = build_ugc_factory_plan(_brief(clip_audio_urls=["https://audio.example/ok.mp3", "notaurl"]))
    assert malformed["ok"] is False
    check = next(c for c in malformed["gate"]["checks"] if c["name"] == "clip_audio_urls_https")
    assert check["passed"] is False


def test_url_validation_parses_host_and_rejects_embedded_credentials():
    for bad in (
        "https://user:pass@assets.example/x.png",  # embedded credentials
        "https:///no-host.png",                     # hostless
        "http://insecure.example/x.png",            # wrong scheme
        "javascript:alert(1)",                      # not a URL at all
    ):
        plan = build_ugc_factory_plan(_brief(casting_reference_urls=[bad]))
        assert plan["ok"] is False, bad
        plan = build_ugc_factory_plan(_brief(clip_audio_urls=[bad]))
        assert plan["ok"] is False, bad
    ok = build_ugc_factory_plan(_brief(casting_reference_urls=["https://assets.example/x.png?token=abc#frag"]))
    assert ok["ok"], ok["gate"]


def test_reference_cap_is_12_combined_reference_files_seed_not_counted():
    from api.services.provider_contracts import MAX_REFERENCE_FILES

    assert MAX_REFERENCE_FILES == 12
    over = build_ugc_factory_plan(_brief(casting_reference_urls=[f"https://assets.example/{i}.png" for i in range(13)]))
    assert over["ok"] is False
    # Exactly 12 reference files + scalar seed + target audio is legal: the
    # published cap counts only the reference lists.
    at_cap = build_ugc_factory_plan(_brief(
        casting_reference_urls=[f"https://assets.example/{i}.png" for i in range(12)],
        clip_audio_urls=["https://audio.example/voice.mp3"],
    ))
    assert at_cap["ok"], at_cap["gate"]


@pytest.mark.asyncio
async def test_executor_preflight_blocks_over_cap_reference_list(tmp_path, ledger):
    provider = RefProvider()
    brief = _brief(casting_reference_urls=[f"https://assets.example/{i}.png" for i in range(12)])
    # Sneak a 13th past the plan gate by mutating the plan the executor reads:
    # preflight pricing must still refuse before any reservation or HTTP.
    import api.services.ugc_executor as ex

    original_build = ex.build_ugc_factory_plan

    def over_cap_plan(brief_arg):
        plan = original_build(brief_arg)
        plan["brief"]["casting_reference_urls"] = plan["brief"]["casting_reference_urls"] + ["https://assets.example/13.png"]
        return plan

    ex.build_ugc_factory_plan = over_cap_plan
    try:
        result = await _execute(brief, provider, tmp_path)
    finally:
        ex.build_ugc_factory_plan = original_build
    assert result["ok"] is False
    assert result["error"] == "provider_reference_files_cap_exceeded"
    assert result["state"] == "preflight_blocked"
    assert provider.submit_calls == []


@pytest.mark.asyncio
async def test_fal_reference_cap_enforced_pre_send_zero_http(monkeypatch):
    calls = []
    provider = _fal(
        monkeypatch, calls,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="reference_image_urls",
        FAL_PROMPT_EXPANSION_MODE="balanced",
    )
    result = await provider.submit_video(prompt="clip", reference_image_urls=[f"https://assets.example/{i}.png" for i in range(13)])
    assert result["ok"] is False
    assert result["error"] == "fal_reference_files_cap_exceeded"
    assert result["charge_outcome"] == "not_sent"
    assert calls == []
    # 12 reference files + seed + audio submits: seed/audio are NOT in the cap.
    ok = await provider.submit_video(
        prompt="clip", image_url="https://storage.example/seed.jpg",
        reference_image_urls=[f"https://assets.example/{i}.png" for i in range(12)],
        duration="10",
    )
    assert ok["ok"] is True, ok
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_fal_prompt_expansion_mode_required_on_reference_route(monkeypatch):
    calls = []
    provider = _fal(
        monkeypatch, calls,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="reference_image_urls",
        # FAL_PROMPT_EXPANSION_MODE deliberately unset
    )
    result = await provider.submit_video(prompt="clip", reference_image_urls=REFS)
    assert result["ok"] is False
    assert result["error"] == "fal_reference_images_not_configured"
    assert "FAL_PROMPT_EXPANSION_MODE" in result["missing"]
    assert result["charge_outcome"] == "not_sent"
    assert calls == []
    assert provider.estimate_clip_cost_cents(reference_image_urls=REFS) is None


@pytest.mark.asyncio
async def test_fal_field_collisions_fail_closed_zero_http(monkeypatch):
    # Audio-URL field colliding with the BOOLEAN generate_audio field.
    calls = []
    provider = _fal(monkeypatch, calls, FAL_AUDIO_URL_FIELD="generate_audio", FAL_AUDIO_INPUT_FIELD="generate_audio")
    result = await provider.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3")
    assert result["ok"] is False
    assert result["error"] == "fal_audio_url_not_configured"
    assert result["charge_outcome"] == "not_sent"
    assert calls == []

    # Reference-LIST field colliding with the SCALAR start-frame field.
    calls2 = []
    provider2 = _fal(
        monkeypatch, calls2,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="image_url",
        FAL_IMAGE_INPUT_FIELD="image_url",
        FAL_PROMPT_EXPANSION_MODE="balanced",
    )
    result2 = await provider2.submit_video(prompt="clip", reference_image_urls=REFS)
    assert result2["ok"] is False
    assert result2["error"] == "fal_reference_images_not_configured"
    assert result2["charge_outcome"] == "not_sent"
    assert calls2 == []


@pytest.mark.asyncio
async def test_fal_audio_duration_floor_documented_constraint(monkeypatch):
    calls = []
    provider = _fal(monkeypatch, calls, FAL_AUDIO_URL_FIELD="target_audio_url", FAL_AUDIO_URL_MODELS="fal-ai/minimax/h3-max/text-to-video")
    short = await provider.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3", duration="1")
    assert short["ok"] is False
    assert short["error"] == "fal_audio_duration_too_short"
    assert short["charge_outcome"] == "not_sent"
    assert calls == []
    ok = await provider.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3", duration="5")
    assert ok["ok"] is True, ok
    assert calls[0]["json"]["target_audio_url"] == "https://audio.example/voice.mp3"


# ----------------------------------------------------------- contract lanes


def _gateway(monkeypatch, **env):
    from api.services.universal_media_gateway import UniversalVideoGatewayProvider

    monkeypatch.setenv("GENERATION_GATEWAY_BASE_URL", "https://gateway.example")
    monkeypatch.setenv("GENERATION_GATEWAY_API_KEY", "gw-key")
    monkeypatch.setenv("GENERATION_GATEWAY_TEXT_VIDEO_MODEL", "vendor/text-video")
    for name in ("GENERATION_GATEWAY_REFERENCE_IMAGES_FIELD", "GENERATION_GATEWAY_AUDIO_URL_FIELD", "GENERATION_GATEWAY_AUDIO_URL_MODELS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return UniversalVideoGatewayProvider()


def _job(**kw):
    base = {
        "script": "word " * 20,
        "prompt": "a creator talking to camera",
        "idempotency_key": "job-key-0001",
        "estimated_cost_ceiling_cents": 500,
    }
    base.update(kw)
    return UGCProviderJob(**base)


def test_gateway_plan_job_fails_explicitly_instead_of_dropping_inputs(monkeypatch):
    provider = _gateway(monkeypatch)
    planned = provider.plan_job(_job(reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3", approval_state="approved"))
    assert planned.state == "failed"
    assert planned.failure["error"] == "gateway_reference_images_not_configured"
    assert planned.failure["charge_outcome"] == "not_sent"
    # Inputs are preserved on the job, never silently dropped.
    assert planned.reference_image_urls == REFS
    assert planned.audio_url == "https://audio.example/voice.mp3"

    planned_audio = _gateway(monkeypatch, GENERATION_GATEWAY_REFERENCE_IMAGES_FIELD="reference_image_urls").plan_job(
        _job(reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3", approval_state="approved"))
    assert planned_audio.state == "failed"
    assert planned_audio.failure["error"] == "gateway_audio_url_not_configured"


@pytest.mark.asyncio
async def test_gateway_submit_job_passes_reference_and_audio_through(monkeypatch):
    provider = _gateway(
        monkeypatch,
        GENERATION_GATEWAY_REFERENCE_IMAGES_FIELD="reference_image_urls",
        GENERATION_GATEWAY_AUDIO_URL_FIELD="target_audio_url",
        GENERATION_GATEWAY_AUDIO_URL_MODELS="vendor/text-video",
        GENERATION_GATEWAY_ESTIMATED_CLIP_COST_CENTS="80",
    )
    captured = {}

    async def fake_submit_video(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "provider": "gateway", "request_id": "gw-1", "status_url": "https://gateway.example/status/1"}

    provider.submit_video = fake_submit_video
    planned = provider.plan_job(_job(reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3", approval_state="approved"))
    assert planned.state == "planned", planned.failure
    assert planned.estimated_cost_cents > 0
    submitted = await provider.submit_job(_job(reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3", approval_state="approved"))
    assert submitted.state == "submitted", submitted.failure
    assert captured["reference_image_urls"] == REFS
    assert captured["audio_url"] == "https://audio.example/voice.mp3"


def test_fal_plan_job_prices_full_contract_and_fails_explicitly(monkeypatch):
    from api.services import media_generation

    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setenv("FAL_TEXT_VIDEO_MODEL", "fal-ai/minimax/h3-max/text-to-video")
    monkeypatch.setenv("FAL_REFERENCE_VIDEO_MODEL", "fal-ai/minimax/h3-max/reference-to-video")
    monkeypatch.setenv("FAL_REFERENCE_IMAGES_FIELD", "reference_image_urls")
    monkeypatch.delenv("FAL_AUDIO_URL_FIELD", raising=False)
    monkeypatch.setenv("FAL_PROMPT_EXPANSION_MODE", "balanced")
    provider = media_generation.FalVideoProvider()

    planned = provider.plan_job(_job(reference_image_urls=REFS, approval_state="approved"))
    assert planned.state == "planned"
    assert planned.model_name == "fal-ai/minimax/h3-max/reference-to-video"
    assert planned.estimated_cost_cents == 80

    unpriceable = provider.plan_job(_job(audio_url="https://audio.example/voice.mp3", approval_state="approved"))
    assert unpriceable.state == "failed"
    assert unpriceable.failure["error"] == "fal_capability_not_configured_for_job_inputs"
    assert unpriceable.audio_url == "https://audio.example/voice.mp3"  # preserved, not dropped


@pytest.mark.asyncio
async def test_neutral_job_and_brief_behavior_unchanged(monkeypatch, tmp_path, ledger):
    """No refs, no audio: the R4e behavior is preserved bit for bit."""
    calls = []
    provider = _fal(monkeypatch, calls)
    result = await provider.submit_video(prompt="clip")
    assert result["ok"] is True, result
    body = calls[0]["json"]
    assert "reference_image_urls" not in body
    assert "target_audio_url" not in body
    assert calls[0]["url"].endswith("fal-ai/minimax/h3-max/text-to-video")

    neutral = RefProvider()
    result = await _execute(_brief(), neutral, tmp_path)
    assert result["state"] == "needs_performance_review", result
    clip1, clip2 = neutral.submit_calls
    assert "reference_image_urls" not in clip1 and "reference_image_urls" not in clip2
    assert "audio_url" not in clip1 and "audio_url" not in clip2
    assert result["provider_pricing"]["priced_with_reference_images"] == {"clip_1": False, "clip_2": False, "seam_retry": False}
    assert result["provider_pricing"]["priced_with_audio_urls"] == {"clip_1": False, "clip_2": False, "seam_retry": False}


def test_provider_job_validators_reject_credentials_and_hostless():
    base = {
        "script": "word " * 20,
        "prompt": "a creator talking to camera",
        "idempotency_key": "job-key-0001",
        "estimated_cost_ceiling_cents": 500,
    }
    with pytest.raises(Exception):
        UGCProviderJob(**base, reference_image_urls=["https://user:pass@assets.example/x.png"])
    with pytest.raises(Exception):
        UGCProviderJob(**base, reference_image_urls=["https:///no-host.png"])
    with pytest.raises(Exception):
        UGCProviderJob(**base, audio_url="https://user:pass@audio.example/v.mp3")


# ============================================================ R3 corrections


class AudioRatedProvider(RefProvider):
    """Prices audio-shaped calls higher, and fails clip 2 with a transport
    exception AT/AFTER send (uncertain_after_send, never a definite zero)."""

    def estimate_clip_cost_cents(self, model_name=None, *, image_url=None, reference_image_urls=None, audio_url=None):
        return 90 if audio_url else 80

    async def submit_video(self, **kwargs):
        self.submit_calls.append(dict(kwargs))
        n = len(self.submit_calls)
        if n == 2:
            raise ConnectionError("simulated transport failure at/after send")
        return {
            "ok": True,
            "provider": "fal",
            "model": "fake/model",
            "request_id": f"req-{n}",
            "response_url": f"https://queue.fal.run/response/{n}",
            "status_url": f"https://queue.fal.run/status/{n}",
        }


@pytest.mark.asyncio
async def test_receipt_settlement_carries_full_per_attempt_audio_pricing(tmp_path, ledger):
    """Regression: the per-attempt receipt estimate must include the audio URL
    (before the fix, a 90c audio-shaped call carried the 80c non-audio rate on
    its receipt, undercounting settlement after a partial failure)."""
    from api.services.factory_runner import _settlement_cents

    provider = AudioRatedProvider()
    receipts = []
    brief = _brief(clip_audio_urls=["https://audio.example/voice-1.mp3"])  # clip 1 voiced, clip 2 not
    # Mixed shapes price the run at ceil((90 + 2x80) x 1.25) = 313c -> 4 ad credits.
    result = await _execute(brief, provider, tmp_path, sink=receipts, ad_credits=4)
    assert result["state"] == "clip_2_failed", result.get("state")
    assert len(receipts) == 2
    clip1, clip2 = receipts
    assert clip1["outcome"] == "accepted"
    assert clip1["estimated_cents"] == 90  # audio-shaped rate on the receipt
    assert clip2["outcome"] == "uncertain_after_send"  # classification retained
    assert clip2["estimated_cents"] == 80  # clip 2's OWN no-audio shape
    settled = _settlement_cents(receipts, fallback_per_clip_cents=90)
    assert settled == {"definite_cents": 90, "uncertain_estimated_cents": 80, "rejected_calls": 0}
    # The run's reservation priced the same mixed shapes: (90 + 2x80) with the plan's 1.25 safety factor.
    plan = build_ugc_factory_plan(brief)
    pricing = estimate_factory_generation_cost(provider, plan, None, image_url=None, reference_image_urls=None, clip_audio_urls=["https://audio.example/voice-1.mp3"])
    assert pricing["estimated_generation_cost_cents"] == 313
    assert pricing["clip_costs_cents"] == {"clip_1": 90, "clip_2": 80, "seam_retry": 80}


@pytest.mark.asyncio
async def test_fal_direct_submit_validates_parsed_urls_and_route_allowlist(monkeypatch):
    # Non-https reference URL on a direct submit: blocked pre-send, zero HTTP.
    calls = []
    provider = _fal(
        monkeypatch, calls,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="reference_image_urls",
        FAL_PROMPT_EXPANSION_MODE="balanced",
    )
    bad = await provider.submit_video(prompt="clip", reference_image_urls=["http://insecure.example/x.png"])
    assert bad["error"] == "fal_invalid_reference_url"
    assert bad["charge_outcome"] == "not_sent"
    assert calls == []

    # Credential-bearing audio URL: blocked pre-send, zero HTTP.
    calls2 = []
    provider2 = _fal(monkeypatch, calls2, FAL_AUDIO_URL_FIELD="target_audio_url", FAL_AUDIO_URL_MODELS="fal-ai/minimax/h3-max/text-to-video")
    bad2 = await provider2.submit_video(prompt="clip", audio_url="https://user:pass@audio.example/v.mp3")
    assert bad2["error"] == "fal_invalid_audio_url"
    assert calls2 == []

    # Field configured but the SELECTED ROUTE not allowlisted: blocked, zero HTTP.
    calls3 = []
    provider3 = _fal(monkeypatch, calls3, FAL_AUDIO_URL_FIELD="target_audio_url")  # no FAL_AUDIO_URL_MODELS
    refused = await provider3.submit_video(prompt="clip", audio_url="https://audio.example/voice.mp3")
    assert refused["ok"] is False
    assert refused["error"] == "fal_audio_url_not_configured"
    assert any("FAL_AUDIO_URL_MODELS" in m for m in refused["missing"])
    assert calls3 == []

    # Reference route selected, allowlist covers only the text route: blocked.
    calls4 = []
    provider4 = _fal(
        monkeypatch, calls4,
        FAL_REFERENCE_VIDEO_MODEL="fal-ai/minimax/h3-max/reference-to-video",
        FAL_REFERENCE_IMAGES_FIELD="reference_image_urls",
        FAL_PROMPT_EXPANSION_MODE="balanced",
        FAL_AUDIO_URL_FIELD="target_audio_url",
        FAL_AUDIO_URL_MODELS="fal-ai/minimax/h3-max/text-to-video",
    )
    refused4 = await provider4.submit_video(prompt="clip", reference_image_urls=REFS, audio_url="https://audio.example/voice.mp3")
    assert refused4["ok"] is False
    assert refused4["error"] == "fal_audio_url_not_configured"
    assert calls4 == []


@pytest.mark.asyncio
async def test_gateway_shared_preflight_covers_estimate_plan_and_submit(monkeypatch):
    # Over-cap reference list: unpriceable, unplanned, unsubmitted - zero HTTP.
    many = [f"https://assets.example/{i}.png" for i in range(13)]
    provider = _gateway(monkeypatch, GENERATION_GATEWAY_REFERENCE_IMAGES_FIELD="reference_image_urls")
    assert provider.estimate_clip_cost_cents(reference_image_urls=many) is None
    with pytest.raises(Exception):
        _job(reference_image_urls=many)  # the contract lane rejects over-cap jobs outright
    result = await provider.submit_video(prompt="clip", reference_image_urls=many)
    assert result["error"] == "gateway_reference_files_cap_exceeded"
    assert result["charge_outcome"] == "not_sent"

    # Non-https reference URL: invalid on every surface.
    assert provider.estimate_clip_cost_cents(reference_image_urls=["http://insecure.example/x.png"]) is None
    bad = await provider.submit_video(prompt="clip", reference_image_urls=["http://insecure.example/x.png"])
    assert bad["error"] == "gateway_invalid_reference_url"
    assert bad["charge_outcome"] == "not_sent"

    # Audio field colliding with the boolean field: capability disabled everywhere.
    colliding = _gateway(monkeypatch, GENERATION_GATEWAY_AUDIO_URL_FIELD="generate_audio")  # == GENERATION_GATEWAY_AUDIO_FIELD default
    assert colliding.estimate_clip_cost_cents(audio_url="https://audio.example/v.mp3") is None
    blocked = await colliding.submit_video(prompt="clip", audio_url="https://audio.example/v.mp3")
    assert blocked["error"] == "gateway_audio_url_not_configured"
    assert blocked["charge_outcome"] == "not_sent"

    # Field configured but selected route not allowlisted.
    unrouted = _gateway(monkeypatch, GENERATION_GATEWAY_AUDIO_URL_FIELD="target_audio_url")
    assert unrouted.estimate_clip_cost_cents(audio_url="https://audio.example/v.mp3") is None
    blocked2 = await unrouted.submit_video(prompt="clip", audio_url="https://audio.example/v.mp3")
    assert blocked2["error"] == "gateway_audio_url_not_configured"
    assert any("GENERATION_GATEWAY_AUDIO_URL_MODELS" in m for m in blocked2["missing"])
