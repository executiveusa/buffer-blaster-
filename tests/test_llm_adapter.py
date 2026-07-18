import pytest

from api.services import llm_adapter


@pytest.mark.parametrize(
    ("provider", "env_name", "model"),
    [
        ("anthropic", "ANTHROPIC_MODEL", "anthropic-test-model"),
        ("openai", "OPENAI_MODEL", "openai-test-model"),
        ("google", "GOOGLE_MODEL", "google-test-model"),
        ("ollama", "OLLAMA_MODEL", "ollama-test-model"),
    ],
)
def test_active_model_reads_provider_configuration(monkeypatch, provider, env_name, model):
    monkeypatch.setenv(env_name, model)

    assert llm_adapter.active_model(provider) == model


def test_active_model_requires_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_MODEL is required"):
        llm_adapter.active_model("openai")


def test_active_provider_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("ACTIVE_LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="unknown provider"):
        llm_adapter.active_provider()
