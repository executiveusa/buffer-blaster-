"""LLM adapter — model-agnostic provider switching.

The platform never hardcodes a model. `chat()` routes to whichever provider is
active (ACTIVE_LLM_PROVIDER). On the VPS, install the provider SDK and the
matching branch activates; in dev it returns a clear stub.
"""
from __future__ import annotations

import os

PROVIDERS = ("anthropic", "openai", "google", "ollama")


def active_provider() -> str:
    return os.getenv("ACTIVE_LLM_PROVIDER", "anthropic")


async def chat(prompt: str, *, system: str = "", max_tokens: int = 1024) -> str:
    """Send a chat completion to the active LLM provider.

    Returns the assistant's text. In dev (no key set) it returns a stub so the
    pipeline can be exercised end-to-end without burning tokens.
    """
    provider = active_provider()
    key = os.getenv(f"{provider.upper()}_API_KEY") if provider != "ollama" else "set"

    if not key:
        return (
            f"[{provider} not configured] Set {provider.upper()}_API_KEY in .env "
            f"to enable live generation. Prompt was: {prompt[:80]}…"
        )

    # On the VPS, dispatch to the real SDK. Kept here so the contract is clear.
    if provider == "anthropic":
        return await _anthropic(prompt, system, max_tokens, key)
    if provider == "openai":
        return await _openai(prompt, system, max_tokens, key)
    if provider == "google":
        return await _google(prompt, system, max_tokens, key)
    if provider == "ollama":
        return await _ollama(prompt, system, max_tokens)
    raise ValueError(f"unknown provider: {provider}")


async def _anthropic(prompt: str, system: str, max_tokens: int, key: str) -> str:
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
                "model": "claude-3-5-sonnet-latest",
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["content"][0]["text"]


async def _openai(prompt: str, system: str, max_tokens: int, key: str) -> str:
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "gpt-4o",
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


async def _google(prompt: str, system: str, max_tokens: int, key: str) -> str:
    # Minimal Gemini text call.
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-pro:generateContent?key={key}",
            json={
                "contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _ollama(prompt: str, system: str, max_tokens: int) -> str:
    import httpx
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{base}/api/generate",
            json={"model": "llama3", "prompt": prompt, "system": system,
                  "stream": False, "options": {"num_predict": max_tokens}},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"]
