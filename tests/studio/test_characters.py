"""Locked house characters: Jalen fills the brief, prompts carry his voice, Kling binds face+voice once a voice id exists."""
import pytest

from api.services import characters
from api.services.characters import apply_character, kling_elements, list_characters, load_character, reference_paths, voice_sample_path
from api.services.ugc_executor import execute_ugc_factory_ad
from api.services.ugc_factory import UGCFactoryBrief, build_ugc_factory_plan
from cli import render_local
from tests.studio.test_ugc_single_clip_ad import EndCardMediaOps, RecordingProvider
from tests.studio.test_ugc_executor import FakeStorage

LINE = "Everett don't get collabs. Till now. Postatees and Mariner High, embroidered, not printed. Seventy on pre-sale. One run only."


def _brief(**overrides):
    values = {
        "character": "jalen",
        "product": "Postatees x Mariner High hoodie",
        "audience": "Mariner High students and families in Everett",
        "pain": "school gear that looks like everyone else's",
        "mechanism": "a one-run collab hoodie made with the school",
        "scripts": (LINE,),
        "clip_count": 1,
        "clip_duration_seconds": 10,
        "avoid": "Seattle Mariners MLB logos",
    }
    values.update(overrides)
    return UGCFactoryBrief(**values)


SAVED_VOICE = "952742773105512039"


@pytest.fixture(autouse=True)
def _no_voice_env(monkeypatch):
    monkeypatch.delenv("CHARACTER_JALEN_KLING_VOICE_ID", raising=False)
    load_character.cache_clear()
    yield
    load_character.cache_clear()


@pytest.fixture
def unlocked(tmp_path, monkeypatch):
    """A copy of the cast where Jalen has no saved voice yet."""
    import json, shutil
    root = tmp_path / "characters"
    shutil.copytree(characters.CHARACTERS_DIR, root)
    path = root / "jalen" / "character.json"
    data = json.loads(path.read_text())
    data["voice"]["kling_voice_id"] = ""
    path.write_text(json.dumps(data))
    monkeypatch.setattr(characters, "CHARACTERS_DIR", root)
    load_character.cache_clear()


def test_jalen_ships_with_refs_and_voice_sample():
    jalen = load_character("jalen")
    assert jalen["name"] == "Jalen"
    assert [p.name for p in reference_paths(jalen)][0] == "ref-hero-hood-down.jpg"
    assert len(reference_paths(jalen)) == 3
    assert voice_sample_path(jalen) is not None
    assert {"id": "jalen", "name": "Jalen", "voice_locked": True} in list_characters()
    assert jalen["voice"]["kling_voice_id"] == SAVED_VOICE


def test_unknown_or_unsafe_character_ids_are_refused():
    for bad in ("nobody", "../etc", "Jalen"):
        with pytest.raises(ValueError, match="unknown_character"):
            load_character(bad)


def test_character_fills_brief_and_merges_rules():
    filled = apply_character({"character": "jalen", "actor_description": "", "delivery_tone": "", "setting": "", "pronunciation_notes": "", "avoid": "MLB logos"})
    assert "deep navy" in filled["actor_description"]
    assert "parked car" in filled["setting"]
    assert "POH-stuh-teez" in filled["pronunciation_notes"]
    assert "sleeve lettering" in filled["avoid"] and "MLB logos" in filled["avoid"]


def test_plan_prompt_carries_look_voice_delivery_and_phonetic_name(unlocked):
    plan = build_ugc_factory_plan(_brief())
    assert plan["ok"], plan["gate"]
    prompt = plan["clips"][0]["prompt"]
    assert "Jalen" in prompt and "deep navy" in prompt
    assert "VOICE:" in prompt and "rasp" in prompt
    assert "DELIVERY:" in prompt
    assert "Poh-stuh-teez" in prompt  # said phonetically in the dialogue
    assert plan["clips"][0]["script"] == LINE  # captions keep the real spelling
    assert plan["character"] == {"id": "jalen", "name": "Jalen", "voice_locked": False, "note": plan["character"]["note"]}
    assert plan["clips"][0]["bind_character"] is False
    assert "@Element1" not in prompt


def test_brief_without_character_is_unchanged():
    plan = build_ugc_factory_plan(_brief(character=""))
    assert plan["character"] is None
    assert "Jalen" not in plan["clips"][0]["prompt"]


def test_saved_voice_id_binds_face_and_voice():
    plan = build_ugc_factory_plan(_brief())
    assert plan["character"]["voice_locked"] is True
    assert plan["clips"][0]["bind_character"] is True
    assert "@Element1" in plan["clips"][0]["prompt"]
    elements = kling_elements(load_character("jalen"))
    assert elements[0]["voice_id"] == SAVED_VOICE
    assert elements[0]["frontal_image_url"].startswith("data:image/jpeg;base64,")
    assert 1 <= len(elements[0]["reference_image_urls"]) <= 3


@pytest.mark.asyncio
async def test_executor_sends_elements_only_when_voice_locked(tmp_path, monkeypatch, unlocked):
    for voice, expect in (("", False), ("829877809978941442", True)):
        monkeypatch.setenv("CHARACTER_JALEN_KLING_VOICE_ID", voice)
        load_character.cache_clear()
        provider = RecordingProvider()
        await execute_ugc_factory_ad(
            _brief(product_reference_url="https://cdn.example/frame.jpg"),
            approved=True, offer_id="trial-7", remaining_provider_budget_cents=400, remaining_ad_credits=3,
            provider=provider, storage=FakeStorage(), media_ops=EndCardMediaOps(), work_root=tmp_path / voice, poll_interval_seconds=0,
        )
        assert ("elements" in provider.submissions[0]) is expect


def test_keyframe_uses_character_photos_first(tmp_path):
    product = tmp_path / "hoodie.jpg"
    product.write_bytes(b"x")
    refs = render_local.character_references(_brief(), [product])
    assert refs[0].name == "ref-hero-hood-down.jpg" and refs[-1] == product
    assert "same man" in render_local.keyframe_prompt(build_brief_for_keyframe())


def build_brief_for_keyframe():
    plan_fields = apply_character({"character": "jalen", "actor_description": "", "delivery_tone": "", "setting": "", "pronunciation_notes": "", "avoid": ""})
    return _brief(**{k: v for k, v in plan_fields.items() if k != "voice_description"}, voice_description=plan_fields["voice_description"])


def test_voice_create_refuses_without_approval(monkeypatch, unlocked):
    import asyncio
    monkeypatch.setenv("FAL_KEY", "test-not-real")
    result = asyncio.run(render_local.voice_create("jalen", 0))
    assert result == {"ok": False, "error": "approval_below_quote", "quote_cents": 1, "approved_cents": 0}


def test_voice_create_is_a_no_op_once_locked(monkeypatch):
    import asyncio
    monkeypatch.setenv("FAL_KEY", "test-not-real")
    assert asyncio.run(render_local.voice_create("jalen", 0)) == {"ok": True, "already_locked": True, "voice_id": SAVED_VOICE}
