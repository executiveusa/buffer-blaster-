"""Consistent-character registry and waste guards (no spend anywhere)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.services.consistency import compile_shot_prompt, resolve_provider_caps, shot_preflight
from api.services.media_contracts import ProviderCapabilities
from tests.journey_support import TEST_OPERATOR_KEY, patch_journey_boundary

P = [f"https://storage.example/refs/{i}.jpg" for i in range(4)]
GOOD_SHOT = {
    "duration_seconds": 10, "aspect_ratio": "9:16", "hero_frame_approved": True,
    "hero_frame_url": "https://storage.example/hero.jpg",
    "identity_block": "Woman, short copper hair, green linen shirt, small silver hoop earrings.",
    "motion_block": "Camera: slow push-in. She lifts the mug and smiles at the lens.",
    "takes_existing": 0, "takes_requested": 2,
}
CAPS = {"supported_durations": [5, 10], "supported_ratios": ["9:16", "16:9"], "accepts_image": True}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("BLASTER_API_KEY", TEST_OPERATOR_KEY)
    patch_journey_boundary()
    return TestClient(app), {"Authorization": f"Bearer {TEST_OPERATOR_KEY}"}


def test_good_shot_passes_and_compiles_two_block_prompt():
    result = shot_preflight(GOOD_SHOT, identity={"photos": P, "consistency_ready": True}, provider_caps=CAPS)
    assert result["ok"] is True, result
    assert result["compiled_prompt"].startswith("Woman, short copper hair")
    assert result["paid_generation"] is False


@pytest.mark.parametrize("change, expected", [
    ({"hero_frame_approved": False}, "approve a hero frame"),
    ({"duration_seconds": 20}, "split it into scenes"),
    ({"duration_seconds": 8}, "does not support 8s"),
    ({"aspect_ratio": "1:1"}, "aspect ratio 1:1"),
    ({"takes_existing": 3, "takes_requested": 2}, "at most 4 takes"),
    ({"motion_block": "A 34-year-old woman with copper hair walks in."}, "never state age"),
    ({"identity_block": "Woman, copper hair. Camera orbits as she walks."}, "motion/camera words"),
])
def test_each_waste_reason_blocks_before_spend(change, expected):
    result = shot_preflight({**GOOD_SHOT, **change}, provider_caps=CAPS)
    assert result["ok"] is False
    assert any(expected in b for b in result["blockers"]), result["blockers"]


def test_model_without_image_input_and_photoless_character_block():
    result = shot_preflight(GOOD_SHOT, identity={"photos": [], "consistency_ready": False}, provider_caps={**CAPS, "accepts_image": False})
    assert any("cannot take the hero frame" in b for b in result["blockers"])
    assert any("no photos" in b for b in result["blockers"])


def test_thin_character_warns_but_does_not_block():
    result = shot_preflight(GOOD_SHOT, identity={"photos": P[:1], "consistency_ready": False}, provider_caps=CAPS)
    assert result["ok"] is True and result["warnings"]


def test_prompt_compiler_references():
    out = compile_shot_prompt("Ceramic mug, matte sage glaze.", "Camera: orbit left, steam rises.", references=3)
    assert out["ok"] and out["prompt"].startswith("Keep the subject identical to reference images @1-@3.")


def test_identity_crud_over_rest_and_mcp_with_agent_scopes(env):
    client, human = env
    bad = client.post("/api/studio/identities", json={"kind": "character", "name": "Ana", "photos": ["http://insecure/x.jpg"]}, headers=human).json()
    assert bad["ok"] is False and "https" in " ".join(bad["problems"])
    made = client.post("/api/studio/identities", json={"kind": "character", "name": "Ana", "photos": P[:2]}, headers=human).json()
    assert made["ok"] and made["identity"]["consistency_ready"] is False and made["identity"]["next"]
    ident_id = made["identity"]["identity_id"]
    upd = client.patch(f"/api/studio/identities/{ident_id}", json={"sheet_url": "https://storage.example/sheet.jpg"}, headers=human).json()
    assert upd["identity"]["consistency_ready"] is True
    last = client.patch(f"/api/studio/identities/{ident_id}", json={"remove_photos": P[:2]}, headers=human).json()
    assert last["ok"] is False and "at least one photo" in " ".join(last["problems"])

    token = client.post("/api/agent/tokens", json={"name": "planner", "scopes": ["read", "plan"]}, headers=human).json()["token"]
    agent = {"Authorization": f"Bearer {token}"}
    rpc = lambda name, args: client.post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}, headers=agent).json()["result"]["structuredContent"]
    listed = rpc("list_identities", {"kind": "character"})
    assert [i["name"] for i in listed["identities"]] == ["Ana"]
    pre = rpc("preflight_shot", {"shot": GOOD_SHOT, "identity_id": ident_id, "provider_caps": CAPS})
    assert pre["ok"] is True, pre
    missing = rpc("preflight_shot", {"shot": GOOD_SHOT, "identity_id": "nope", "provider_caps": CAPS})
    assert missing["ok"] is False


def test_every_recipe_shot_passes_the_waste_guard_with_an_identity_block():
    from api.services.recipes import RECIPES
    for recipe in RECIPES:
        for shot in recipe["shots"]:
            result = shot_preflight({**GOOD_SHOT, "duration_seconds": shot["seconds"], "motion_block": shot["motion"]},
                                    provider_caps={**CAPS, "supported_durations": [5, 10]})
            assert result["ok"], (recipe["id"], shot, result["blockers"])


def _fake_provider(configured: bool, caps: ProviderCapabilities):
    return SimpleNamespace(configured=configured, capabilities=lambda: caps)


def test_configured_provider_caps_override_caller_supplied_caps(monkeypatch):
    """Caps autofill: a configured provider's env-driven caps always win.

    Callers never pass caps by hand - permissive caller caps must not loosen
    the waste guards before spend.
    """
    fake = _fake_provider(True, ProviderCapabilities(
        provider="fal", image_to_video=False,
        supported_ratios=["9:16"], supported_durations_seconds=[10]))
    monkeypatch.setattr("api.services.consistency.get_media_provider", lambda: fake)
    permissive = {"supported_durations": [], "supported_ratios": [], "accepts_image": True}
    result = shot_preflight({**GOOD_SHOT, "aspect_ratio": "16:9"}, provider_caps=permissive)
    assert result["ok"] is False
    assert any("aspect ratio 16:9" in b for b in result["blockers"])
    assert any("cannot take the hero frame" in b for b in result["blockers"])
    assert result["provider_caps"]["server_derived"] is True
    assert result["provider_caps"]["provider"] == "fal"


def test_unconfigured_provider_falls_back_to_caller_caps(monkeypatch):
    fake = _fake_provider(False, ProviderCapabilities(provider="gateway"))
    monkeypatch.setattr("api.services.consistency.get_media_provider", lambda: fake)
    result = shot_preflight(GOOD_SHOT, provider_caps=CAPS)
    assert result["ok"] is True, result
    assert result["provider_caps"]["server_derived"] is False


def test_mcp_preflight_shot_autofills_server_caps(env, monkeypatch):
    """Router level: preflight_shot without provider_caps gets server caps."""
    client, headers = env
    fake = _fake_provider(True, ProviderCapabilities(
        provider="fal", image_to_video=True,
        supported_ratios=["9:16"], supported_durations_seconds=[10]))
    monkeypatch.setattr("api.services.consistency.get_media_provider", lambda: fake)
    rpc = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
           "params": {"name": "preflight_shot", "arguments": {"shot": {**GOOD_SHOT, "duration_seconds": 8}}}}
    res = client.post("/api/mcp", json=rpc, headers=headers)
    assert res.status_code == 200
    payload = res.json()["result"]
    text = payload["content"][0]["text"]
    import json as _json
    data = _json.loads(text)
    assert data["ok"] is False
    assert any("does not support 8s" in b for b in data["blockers"])
    assert data["provider_caps"]["server_derived"] is True
