"""LLM adapter — provider and model selection are configuration-driven."""
from __future__ import annotations

import os

PROVIDERS = ("anthropic", "openai", "google", "ollama")
MODEL_ENV_BY_PROVIDER = {
    "anthropic": "ANTHROPIC_MODEL",
    "openai": "OPENAI_MODEL",
    "google": "GOOGLE_MODEL",
    "ollama": "OLLAMA_MODEL",
}


def active_provider() -> str:
    provider = os.getenv("ACTIVE_LLM_PROVIDER", "anthropic")
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    return provider


def active_model(provider: str | None = None) -> str:
    selected_provider = provider or active_provider()
    if selected_provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {selected_provider}")
    env_name = MODEL_ENV_BY_PROVIDER[selected_provider]
    model = os.getenv(env_name)
    if not model:
        raise RuntimeError(f"{env_name} is required for provider {selected_provider}")
    return model


async def chat(prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
    """Send a chat completion to the configured provider and model."""
    provider = active_provider()
    key = os.getenv(f"{provider.upper()}_API_KEY") if provider != "ollama" else "set"

    if not key:
        return (
            f"[{provider} not configured] Set {provider.upper()}_API_KEY in .env "
            f"to enable live generation. Prompt was: {prompt[:80]}…"
        )

    model = active_model(provider)
    if provider == "anthropic":
        return await _anthropic(prompt, system, max_tokens, key, model)
    if provider == "openai":
        return await _openai(prompt, system, max_tokens, key, model)
    if provider == "google":
        return await _google(prompt, system, max_tokens, key, model)
    if provider == "ollama":
        return await _ollama(prompt, system, max_tokens, model)
    raise ValueError(f"unknown provider: {provider}")


async def _anthropic(
    prompt: str,
    system: str,
    max_tokens: int,
    key: str,
    model: str,
) -> str:
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"]


async def _openai(
    prompt: str,
    system: str,
    max_tokens: int,
    key: str,
    model: str,
) -> str:
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _google(
    prompt: str,
    system: str,
    max_tokens: int,
    key: str,
    model: str,
) -> str:
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={key}",
            json={
                "contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _ollama(
    prompt: str,
    system: str,
    max_tokens: int,
    model: str,
) -> str:
    import httpx

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{base}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"]
