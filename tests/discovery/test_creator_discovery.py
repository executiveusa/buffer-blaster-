from fastapi.testclient import TestClient

from api.app import app
from api.services.discovery import discover, get_card, load_cards

client = TestClient(app)


def test_seed_cards_have_provenance_and_unique_ids() -> None:
    cards = load_cards()
    ids = [card["id"] for card in cards]
    hashes = [card["source"]["content_hash"] for card in cards]

    assert len(cards) >= 3
    assert len(ids) == len(set(ids))
    assert len(hashes) == len(set(hashes))

    for card in cards:
        assert card["source"]["repo"]
        assert card["source"]["license"]
        assert isinstance(card["source"]["license_verified"], bool)
        assert card["icm_path"]


def test_discover_returns_three_deterministic_results() -> None:
    first = discover("cinematic instagram launch reel for my clothing brand")
    second = discover("cinematic instagram launch reel for my clothing brand")

    assert len(first) == 3
    assert [card["id"] for card in first] == [card["id"] for card in second]
    assert first[0]["id"] == "bb-video-launch-reel-001"


def test_discover_api_contract() -> None:
    response = client.post(
        "/v1/discover",
        json={"intent": "product photography for ecommerce", "limit": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3
    assert payload["cards"][0]["id"] == "bb-image-product-studio-001"
    assert payload["cards"][0]["source"]["license_verified"] is True


def test_card_detail_accepts_id_and_slug() -> None:
    by_id = get_card("bb-workflow-launch-pack-001")
    by_slug = get_card("one-idea-launch-pack")

    assert by_id is not None
    assert by_slug is not None
    assert by_id["id"] == by_slug["id"]

    response = client.get("/v1/cards/one-idea-launch-pack")
    assert response.status_code == 200
    assert response.json()["card"]["category"] == "Workflows"


def test_card_detail_404() -> None:
    response = client.get("/v1/cards/not-a-real-card")
    assert response.status_code == 404
