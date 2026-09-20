import json

from api.services.gateway_fleet import configured_gateway_providers, gateway_catalog
from api.services.media_generation import get_media_provider, media_providers


def _fleet(monkeypatch):
    monkeypatch.setenv("MUAPI_TEST_KEY", "mu-key")
    monkeypatch.setenv("ROUTER_TEST_KEY", "router-key")
    monkeypatch.setenv(
        "GENERATION_GATEWAYS_JSON",
        json.dumps([
            {
                "name": "muapi",
                "base_url": "https://api.example.test",
                "api_key_env": "MUAPI_TEST_KEY",
                "text_model": "seedance-2.5",
                "image_model": "seedance-2.5",
                "allowed_models": ["seedance-2.5", "kling-3.0"],
                "model_costs_cents": {"seedance-2.5": 40, "kling-3.0": 55},
                "submit_path": "/api/v1/{model}",
                "status_path": "/api/v1/predictions/{id}/result",
                "auth_header": "x-api-key",
                "auth_prefix": "",
                "model_in_body": False,
                "supported_ratios": ["9:16", "16:9"],
                "supported_durations_seconds": [5, 10, 15],
                "commercial_use_status": "approved",
                "commercial_use_approved": True,
                "quality_rank": 72,
                "cost_class": "standard",
                "deployment": "hosted",
            },
            {
                "name": "mediarouter",
                "base_url": "http://mediarouter:8080",
                "api_key_env": "ROUTER_TEST_KEY",
                "text_model": "wan-3.0",
                "image_model": "wan-3.0",
                "allowed_models": ["wan-3.0", "seedance-2.5"],
                "model_costs_cents": {"wan-3.0": 18, "seedance-2.5": 35},
                "submit_path": "/v1/videos",
                "status_path": "/v1/videos/{id}",
                "model_in_body": True,
                "commercial_use_status": "approved",
                "commercial_use_approved": True,
                "quality_rank": 66,
                "cost_class": "low",
                "deployment": "hybrid",
            },
        ]),
    )


def test_gateway_fleet_loads_multiple_server_owned_providers(monkeypatch):
    _fleet(monkeypatch)
    providers = configured_gateway_providers()
    assert set(providers) == {"muapi", "mediarouter"}
    assert providers["muapi"].models() == ["kling-3.0", "seedance-2.5"]
    assert providers["mediarouter"].estimate_clip_cost_cents("wan-3.0") == 18


def test_media_provider_can_be_selected_by_name(monkeypatch):
    _fleet(monkeypatch)
    monkeypatch.delenv("FAL_KEY", raising=False)
    providers = media_providers()
    assert {"muapi", "mediarouter"}.issubset(set(providers))
    assert get_media_provider("muapi").status()["provider"] == "muapi"
    assert get_media_provider("mediarouter").status()["provider"] == "mediarouter"
    assert get_media_provider("missing").configured is False


def test_gateway_catalog_exposes_no_secrets(monkeypatch):
    _fleet(monkeypatch)
    catalog = gateway_catalog()
    encoded = json.dumps(catalog)
    assert "mu-key" not in encoded
    assert "router-key" not in encoded
    assert {item["provider"] for item in catalog} == {"muapi", "mediarouter"}
