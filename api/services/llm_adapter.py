"""LLM adapter — provider and model selection are configuration-driven.

Every provider call is ledgered (S4): an upper-bound estimate is held against
owner caps BEFORE the call (concurrent calls cannot jointly exceed a cap),
and exactly one usage row is recorded after the call with real token counts
from the provider response. actual_cents is recorded only when the provider
reports a cost; otherwise the estimate stands (never silently zero).

Estimates are CONFIGURED, never assumed: each (provider, model) pair needs
its current vendor list price in
LLM_PRICE_{PROVIDER}_{MODEL}_IN/OUT_CENTS_PER_MTOK, grounded in the vendor's
live pricing page before enabling provider calls.
A model without configured pricing is REJECTED before any provider call -
there is no 'conservative default', because no invented number is a verifiable
upper bound across models, tiers and reasoning modes.
"""
from __future__ import annotations

import math
import os
import re

from . import usage_ledger

PROVIDERS = ("anthropic", "openai", "google", "ollama")


class UsageCapExceeded(RuntimeError):
    """Raised when owner caps block an LLM call before it is made."""

    def __init__(self, detail: dict):
        super().__init__(str(detail.get("error", "usage_cap_exceeded")))
        self.detail = detail


class ModelPricingUnconfigured(RuntimeError):
    """Raised before any provider call when the active model has no configured
    vendor-grounded price. We never guess a 'safe' number."""

    def __init__(self, provider: str, model: str, missing: list[str]):
        super().__init__(f"model_pricing_unconfigured: {provider}/{model}")
        self.detail = {"ok": False, "error": "model_pricing_unconfigured",
                       "provider": provider, "model": model, "missing_env": missing,
                       "detail": "Set the model's current vendor list price (cents per million tokens); see docs/USAGE_AND_CAPS.md."}


def _model_env_fragment(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", model).strip("_").upper()


def configured_prices(provider: str, model: str) -> tuple[int, int]:
    """Vendor-grounded prices for exactly this model, or raise. No defaults."""
    frag = f"LLM_PRICE_{provider.upper()}_{_model_env_fragment(model)}"
    missing: list[str] = []
    out: list[int] = []
    for direction in ("IN", "OUT"):
        raw = os.getenv(f"{frag}_{direction}_CENTS_PER_MTOK", "")
        try:
            value = int(raw)
            if value < 0:
                raise ValueError
            out.append(value)
        except ValueError:
            missing.append(f"{frag}_{direction}_CENTS_PER_MTOK")
    if missing:
        raise ModelPricingUnconfigured(provider, model, missing)
    return out[0], out[1]


#: Special/role/framing tokens a provider may add around message content.
#: Anthropic and OpenAI document per-message overhead in single digits;
#: 64 keeps the bound above any documented framing cost.
TOKEN_BOUND_OVERHEAD = 64


def estimate_input_tokens(prompt: str, system: str) -> int:
    """Proven input-token UPPER BOUND (M1): UTF-8 byte length + framing
    overhead. Both tokenizer families in use satisfy tokens <= bytes:
    byte-level BPE (OpenAI, Anthropic, Llama) maps every token to at least
    one byte; SentencePiece/unigram (Google) maps every token to at least
    one character, and characters <= bytes in UTF-8. ceil(chars/4) was NOT a
    bound: CJK (3 bytes/char, ~1 token), emoji (4 bytes, 1-3 tokens) and
    dense code undercounted 3-4x. This bound over-reserves for CJK
    (conservative; the difference is refunded at settle when the provider
    reports token counts).
    """
    return len(prompt.encode("utf-8")) + len(system.encode("utf-8")) + TOKEN_BOUND_OVERHEAD


def estimate_llm_cents(provider: str, model: str, prompt: str, system: str, max_tokens: int) -> int:
    """Upper bound from the CONFIGURED vendor price: proven input bound +
    the full max_tokens output at the model's list price."""
    pin, pout = configured_prices(provider, model)
    est_in = estimate_input_tokens(prompt, system)
    return max(0, math.ceil((est_in * pin + int(max_tokens) * pout) / 1_000_000))


def priced_actual_cents(provider: str, model: str, tokens_in: int, tokens_out: int) -> int:
    """Cost of a completed call computed from the PROVIDER-REPORTED token
    counts at the CONFIGURED vendor list price. This is recorded separately
    as priced_actual_cents (cost_provenance='computed_from_provider_tokens')
    - never in actual_cents, which stays provider-reported only."""
    pin, pout = configured_prices(provider, model)
    return max(0, math.ceil((int(tokens_in) * pin + int(tokens_out) * pout) / 1_000_000))
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


async def chat(prompt: str, *, system: str = "", max_tokens: int = 1024,
               actor: str = "api-key", job_id: str | None = None,
               reasoning_level: str | None = None) -> str:
    """Send a chat completion to the configured provider and model.

    Ledgers exactly one usage row per provider call. Raises UsageCapExceeded
    before any provider call when an owner cap would be exceeded.
    """
    provider = active_provider()
    key = os.getenv(f"{provider.upper()}_API_KEY") if provider != "ollama" else "set"

    if not key:
        return (
            f"[{provider} not configured] Set {provider.upper()}_API_KEY in .env "
            f"to enable live generation. Prompt was: {prompt[:80]}…"
        )

    model = active_model(provider)
    est = 0 if provider == "ollama" else estimate_llm_cents(provider, model, prompt, system, max_tokens)
    hold_result = await usage_ledger.check_and_hold(job_id=job_id, estimated_cents=est)
    if not hold_result.get("ok"):
        raise UsageCapExceeded(hold_result)
    hold = hold_result.get("hold")
    try:
        if provider == "anthropic":
            text, usage = await _anthropic(prompt, system, max_tokens, key, model)
        elif provider == "openai":
            text, usage = await _openai(prompt, system, max_tokens, key, model)
        elif provider == "google":
            text, usage = await _google(prompt, system, max_tokens, key, model)
        elif provider == "ollama":
            text, usage = await _ollama(prompt, system, max_tokens, model)
        else:
            raise ValueError(f"unknown provider: {provider}")
    except Exception:
        await usage_ledger.release_hold(hold)
        raise
    # M1: when the provider reports token counts but no cost, price the
    # tokens at the configured vendor list and settle caps against that
    # LABELED value (actual_cents stays None - provider actuals only).
    # When the provider reports neither, the proven upper-bound reservation
    # stays in cap totals forever (record_usage settles at the estimate).
    priced: int | None = None
    if (
        provider != "ollama"
        and usage.get("actual_cents") is None
        and usage.get("tokens_in") is not None
        and usage.get("tokens_out") is not None
    ):
        priced = priced_actual_cents(provider, model, usage["tokens_in"], usage["tokens_out"])
    entry = await usage_ledger.record_usage(
        actor=actor, provider=provider, model=model, kind="llm", job_id=job_id,
        reasoning_level=reasoning_level,
        tokens_in=usage.get("tokens_in"), tokens_out=usage.get("tokens_out"),
        estimated_cents=est,
        actual_cents=usage.get("actual_cents"),  # only when the provider reported it
        priced_actual_cents=priced,
        cost_provenance="computed_from_provider_tokens" if priced is not None else None,
    )
    await usage_ledger.release_hold(hold)
    if not entry.get("ok"):
        # The call already cost money; losing the row is not acceptable.
        raise RuntimeError(f"usage_ledger_write_failed: {entry.get('error')}")
    return text


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
        body = r.json()
        usage_raw = body.get("usage") or {}
        return body["content"][0]["text"], {
            "tokens_in": usage_raw.get("input_tokens"),
            "tokens_out": usage_raw.get("output_tokens"),
        }


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
        body = r.json()
        usage_raw = body.get("usage") or {}
        return body["choices"][0]["message"]["content"], {
            "tokens_in": usage_raw.get("prompt_tokens"),
            "tokens_out": usage_raw.get("completion_tokens"),
        }


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
        body = r.json()
        usage_raw = body.get("usageMetadata") or {}
        return body["candidates"][0]["content"]["parts"][0]["text"], {
            "tokens_in": usage_raw.get("promptTokenCount"),
            "tokens_out": usage_raw.get("candidatesTokenCount"),
        }


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
        body = r.json()
        return body["response"], {
            "tokens_in": body.get("prompt_eval_count"),
            "tokens_out": body.get("eval_count"),
            "actual_cents": 0,  # self-hosted: provider-reported cost is zero
        }
