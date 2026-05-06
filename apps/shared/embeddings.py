"""
Embeddings client (OpenRouter).

Milestone 7 (Part 1) uses embeddings for vector + hybrid retrieval.

We use the OpenRouter embeddings endpoint:
  POST https://openrouter.ai/api/v1/embeddings
"""

from __future__ import annotations

import os
from typing import Iterable

import requests


class EmbeddingsError(RuntimeError):
    pass


def _base_url() -> str:
    return os.getenv("EMBEDDINGS_BASE_URL", "https://openrouter.ai/api/v1")


def _api_key() -> str:
    key = os.getenv("EMBEDDINGS_API_KEY", "")
    if not key:
        raise EmbeddingsError("Missing EMBEDDINGS_API_KEY")
    return key


def _model() -> str:
    return os.getenv("EMBEDDINGS_MODEL", "google/gemini-embedding-001")


def _dimensions() -> int | None:
    v = os.getenv("EMBEDDINGS_DIMENSIONS", "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError as exc:
        raise EmbeddingsError("EMBEDDINGS_DIMENSIONS must be an integer") from exc


def _post_embeddings(payload: dict) -> dict:
    url = _base_url().rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    try:
        data = resp.json()
    except Exception:
        data = {}

    # OpenRouter often returns useful details in {"error": {...}}.
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or str(err)
        else:
            msg = str(err) if err else resp.text
        raise EmbeddingsError(f"Embeddings request failed ({resp.status_code}): {msg}")
    return data


def _embed_batch(batch: list[str]) -> list[list[float]]:
    """Embed a single batch of texts (internal helper)."""
    payload: dict = {"model": _model(), "input": batch}
    dims = _dimensions()
    if dims:
        payload["dimensions"] = dims

    try:
        data = _post_embeddings(payload)
    except EmbeddingsError as exc:
        # Some providers/models reject `dimensions`.
        if dims:
            msg = str(exc).lower()
            if "dimension" in msg or "dimensions" in msg:
                payload.pop("dimensions", None)
                data = _post_embeddings(payload)
            else:
                raise
        else:
            raise

    items = data.get("data") or []
    vectors: list[list[float]] = []
    for it in items:
        emb = it.get("embedding")
        if not isinstance(emb, list):
            raise EmbeddingsError("Embeddings response missing embedding vectors")
        vectors.append([float(x) for x in emb])

    if len(vectors) != len(batch):
        # Include provider error details if returned.
        if data.get("error"):
            raise EmbeddingsError(
                f"Embeddings count mismatch: expected {len(batch)} got {len(vectors)}. "
                f"Provider error: {data.get('error')}"
            )
        raise EmbeddingsError(
            f"Embeddings count mismatch: expected {len(batch)} got {len(vectors)}. "
            f"Response keys: {list(data.keys())}"
        )
    return vectors


# Maximum texts per API call — keeps requests within provider limits.
_BATCH_SIZE = int(os.getenv("EMBEDDINGS_BATCH_SIZE", "16"))
_MAX_CHARS = int(os.getenv("EMBEDDINGS_MAX_CHARS", "8000"))


def _looks_like_token_limit_error(exc: EmbeddingsError) -> bool:
    msg = str(exc).lower()
    return "token" in msg and "limit" in msg


def _truncate_text(text: str) -> str:
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS]


def _embed_batch_resilient(batch: list[str]) -> list[list[float]]:
    """
    Embed with fallback strategy for provider token limits:
    - Retry with smaller sub-batches when a batch is too large.
    - If a single text is too large, truncate and retry.
    """
    if not batch:
        return []

    try:
        return _embed_batch(batch)
    except EmbeddingsError as exc:
        if not _looks_like_token_limit_error(exc):
            raise

        # Split batch on token-limit errors.
        if len(batch) > 1:
            mid = len(batch) // 2
            left = _embed_batch_resilient(batch[:mid])
            right = _embed_batch_resilient(batch[mid:])
            return left + right

        # Single text still too long: truncate and retry once.
        one = _truncate_text(batch[0])
        if one == batch[0]:
            raise
        return _embed_batch([one])


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """
    Embed multiple texts, automatically batching to stay within API limits.

    Returns a list of vectors in the same order as input texts.
    """
    inputs = list(texts)
    if not inputs:
        return []

    all_vectors: list[list[float]] = []
    for start in range(0, len(inputs), _BATCH_SIZE):
        batch = inputs[start : start + _BATCH_SIZE]
        all_vectors.extend(_embed_batch_resilient(batch))

    return all_vectors


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]
