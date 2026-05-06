"""
Generative LLM client with dual providers:
- OpenRouter chat completions
- Native Gemini API
"""

from __future__ import annotations

import os
import time

import requests

from app.settings import settings


class LLMError(RuntimeError):
    pass


def _effective_max_tokens(max_tokens: int | None) -> int:
    if max_tokens is None:
        return int(settings.chat_max_tokens)
    return max(256, min(int(max_tokens), 8192))


# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------

def _openrouter_base_url() -> str:
    return os.getenv("OPENROUTER_BASE_URL", settings.embeddings_base_url)


def _openrouter_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        key = os.getenv("EMBEDDINGS_API_KEY", "")
    if not key:
        raise LLMError("Missing OPENROUTER_API_KEY or EMBEDDINGS_API_KEY")
    return key


def _fallback_models() -> list[str]:
    raw = os.getenv("CHAT_FALLBACK_MODELS", settings.chat_fallback_models)
    return [m.strip() for m in raw.split(",") if m.strip()]


def _parse_error(resp: requests.Response) -> str:
    err_msg = resp.text
    try:
        err_json = resp.json()
        if "error" in err_json:
            err_msg = str(err_json["error"])
    except ValueError:
        pass
    return err_msg


def _is_retryable_rate_limit(status_code: int, err_msg: str) -> bool:
    if status_code == 429:
        return True
    low = err_msg.lower()
    return "rate-limit" in low or "rate limited" in low or "temporarily rate-limited" in low


def _candidate_models(explicit_model: str | None) -> list[str]:
    primary = explicit_model or settings.chat_model
    out: list[str] = [primary]
    for m in _fallback_models():
        if m not in out:
            out.append(m)
    return out


def _call_openrouter(
    *,
    messages: list[dict[str, str]],
    system_prompt: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int,
    allow_fallbacks: bool = True,
) -> tuple[str, str, str]:
    url = _openrouter_base_url().rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {_openrouter_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AI Legal Knowledge Assistant",
    }

    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(messages)

    models = [model] if (model and not allow_fallbacks) else _candidate_models(model)
    last_error: str | None = None

    for i, candidate in enumerate(models):
        payload = {
            "model": candidate,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
        except requests.RequestException as exc:
            last_error = f"HTTP request failed for model {candidate}: {exc}"
            continue

        if resp.status_code >= 400:
            err_msg = _parse_error(resp)
            last_error = f"OpenRouter API error on model {candidate}: {resp.status_code} {err_msg}"
            if _is_retryable_rate_limit(resp.status_code, err_msg):
                time.sleep(1.2)
            if i < len(models) - 1:
                continue
            raise LLMError(last_error)

        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            last_error = f"No choices returned from model {candidate}. Response: {data}"
            if i < len(models) - 1:
                continue
            raise LLMError(last_error)

        content = (choices[0].get("message") or {}).get("content", "")
        if not content:
            last_error = f"Empty response content from model {candidate}"
            if i < len(models) - 1:
                continue
            raise LLMError(last_error)
        model_used = str(data.get("model") or candidate)
        return content, model_used, "openrouter"

    raise LLMError(last_error or "No OpenRouter chat models available")


# ---------------------------------------------------------------------------
# Gemini Native API
# ---------------------------------------------------------------------------

def _gemini_base_url() -> str:
    return os.getenv("GEMINI_BASE_URL", settings.gemini_base_url)


def _gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", settings.gemini_api_key or "")
    if not key:
        raise LLMError("Missing GEMINI_API_KEY")
    return key


def _gemini_model(explicit_model: str | None) -> str:
    return explicit_model or os.getenv("GEMINI_CHAT_MODEL", settings.gemini_chat_model)


def _gemini_contents(messages: list[dict[str, str]]) -> list[dict]:
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "system":
            # system instruction is passed separately
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": msg.get("content", "")}]})
    return contents


def _call_gemini(
    *,
    messages: list[dict[str, str]],
    system_prompt: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int,
) -> tuple[str, str, str]:
    model_name = _gemini_model(model)
    url = f"{_gemini_base_url().rstrip('/')}/models/{model_name}:generateContent"
    params = {"key": _gemini_api_key()}
    payload: dict = {
        "contents": _gemini_contents(messages),
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    try:
        resp = requests.post(url, params=params, json=payload, timeout=120)
    except requests.RequestException as exc:
        raise LLMError(f"Gemini HTTP request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise LLMError(f"Gemini API error: {resp.status_code} {_parse_error(resp)}")

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError(f"Gemini returned no candidates: {data}")

    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    text_parts = [str(p.get("text", "")) for p in parts if isinstance(p, dict)]
    content = "\n".join(tp for tp in text_parts if tp).strip()
    if not content:
        raise LLMError(f"Gemini returned empty content: {data}")

    model_used = str(data.get("modelVersion") or model_name)
    return content, model_used, "gemini"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_chat_completion(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> str:
    content, _model_used, _provider_used = generate_chat_completion_with_meta(
        messages=messages,
        system_prompt=system_prompt,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return content


def generate_chat_completion_with_meta(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> tuple[str, str, str]:
    provider_name = (provider or settings.llm_provider_default or "openrouter").strip().lower()
    tok = _effective_max_tokens(max_tokens)

    if provider_name == "gemini":
        return _call_gemini(
            messages=messages,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=tok,
        )
    if provider_name == "openrouter":
        return _call_openrouter(
            messages=messages,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=tok,
            allow_fallbacks=True,
        )
    raise LLMError(f"Unsupported llm provider: {provider_name}")

