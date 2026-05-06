# AI Legal System — Analysis & Recommendations

## Part 1: Improving Result Quality

After reviewing the full codebase, here are the key changes ranked by **impact on result quality**:

---

### 🔴 1. Use a Stronger Chat Model (Highest Impact)

**Current Problem:** You're using `google/gemma-4-26b-a4b-it:free` via OpenRouter with fallbacks to `openrouter/free` and `google/gemma-3-4b-it:free`. These are small, free-tier models that struggle with:
- Complex legal reasoning
- Faithful citation grounding
- Structured report generation
- Arabic legal terminology

**Recommendation:** Switch to a high-quality model. Options ranked by cost-effectiveness for legal work:

| Model | Quality | Cost | Best For |
|-------|---------|------|----------|
| `google/gemini-2.5-flash` | ★★★★☆ | ~$0.15/1M input | Best bang for buck — great reasoning, fast |
| `google/gemini-2.5-pro` | ★★★★★ | ~$1.25/1M input | Maximum quality, complex legal analysis |
| `anthropic/claude-sonnet-4` | ★★★★★ | ~$3/1M input | Excellent for nuanced legal writing |
| `openai/gpt-4o` | ★★★★☆ | ~$2.5/1M input | Strong general-purpose |

> [!IMPORTANT]
> The model is the single biggest factor in output quality. Even with perfect prompts and retrieval, a 4B parameter model cannot match the reasoning of Gemini 2.5 Pro or Claude Sonnet. **Upgrading to `google/gemini-2.5-flash` (via OpenRouter or native Gemini API) would give the biggest immediate quality boost.**

---

### 🔴 2. Improve System Prompts (High Impact, Zero Cost)

Your current prompts are functional but miss several techniques that dramatically improve RAG quality:

#### Current Issues:
- No explicit instruction to **structure the answer**
- No instruction to handle **conflicting sources**
- No instruction to note **confidence level**
- No "chain-of-thought" guidance for complex legal questions
- `max_tokens: 2000` is too low for detailed legal analysis

#### Recommended Chat Prompts:

```python
# chat.py — PUBLIC_SYSTEM_PROMPT
PUBLIC_SYSTEM_PROMPT = """You are a helpful AI legal assistant that explains legal concepts in plain language.

## Rules
1. Answer ONLY using the provided Source chunks below. Never invent facts, cases, or laws.
2. If sources are insufficient, say "I don't have enough sources to answer this question" and explain what's missing.
3. When sources contain conflicting information, acknowledge the conflict and present both sides.
4. Cite sources inline using [Chunk ID: <uuid>] so the user can verify your claims.
5. Structure your answer with clear sections if the question has multiple parts.
6. If the question is ambiguous, address the most likely interpretation and note the ambiguity.

## Answering Process
- First, identify which source chunks are relevant to the question
- Then, synthesize the information into a clear, structured answer
- Finally, note any important limitations or caveats

--- SOURCES ---
{sources}
"""

# chat.py — LAWYER_SYSTEM_PROMPT
LAWYER_SYSTEM_PROMPT = """You are an expert AI legal research assistant for professional lawyers.

## Rules
1. Answer ONLY using the provided Source chunks. Never hallucinate facts, cases, statutes, or legal principles.
2. Cite every factual claim with [Chunk ID: <uuid>] inline. Every paragraph must have at least one citation.
3. If the sources are insufficient, explicitly state "Insufficient sources" and describe what additional materials would be needed.
4. When sources present conflicting interpretations, analyze both positions with citations.
5. Use precise legal terminology. Reference specific statute numbers, article numbers, and section references from the sources.
6. Distinguish between binding authority, persuasive authority, and dicta when apparent from the sources.

## Answer Structure
- Start with a direct answer/summary
- Provide detailed analysis with inline citations
- Note any jurisdictional limitations or temporal qualifications
- End with caveats or areas requiring further research

--- SOURCES ---
{sources}
"""
```

---

### 🟡 3. Increase `max_tokens` and `top_k` (Medium Impact)

#### In [llm.py](file:///d:/AI_LegalSystem/apps/api/app/services/llm.py#L118):
```diff
-"max_tokens": 2000,
+"max_tokens": 4096,
```
2000 tokens is often not enough for detailed legal analysis. 4096 gives the model room to provide thorough answers.

#### In [schemas.py](file:///d:/AI_LegalSystem/apps/api/app/schemas.py#L154):
```diff
 class ChatRequest(BaseModel):
     messages: list[ChatMessage]
     filters: SearchFilters | None = None
-    top_k: int = 10
+    top_k: int = 15
     mode: str | None = None

 class ReportRequest(BaseModel):
     query: str
     filters: SearchFilters | None = None
-    top_k: int = 20
+    top_k: int = 25
     mode: str | None = None
```

More source chunks = more context for the model to reason over. With a stronger model, you can feed more chunks without degrading quality.

---

### 🟡 4. Improve Source Context Formatting (Medium Impact)

The current source formatting is minimal. Richer context helps the model reason better:

#### In [chat.py](file:///d:/AI_LegalSystem/apps/api/app/routers/chat.py#L88-L95):
```diff
 for hit in hits:
     jurisdiction = hit.jurisdiction or "Unknown"
     title = hit.document_title or "Unknown Document"
-    source_texts.append(f"[Chunk ID: {hit.chunk_id}]\nDocument: {title} ({jurisdiction})\nSnippet: {hit.snippet}\n")
+    section = " > ".join(hit.section_path) if hit.section_path else "N/A"
+    year = str(hit.year) if hit.year else "N/A"
+    page_ref = f"pp. {hit.page_start}-{hit.page_end}" if hit.page_start else "N/A"
+    citations = ", ".join(hit.citations[:5]) if hit.citations else "None"
+    source_texts.append(
+        f"[Chunk ID: {hit.chunk_id}]\n"
+        f"Document: {title}\n"
+        f"Jurisdiction: {jurisdiction} | Year: {year} | Section: {section}\n"
+        f"Pages: {page_ref} | Referenced Citations: {citations}\n"
+        f"Text:\n{hit.snippet}\n"
+    )
```

This gives the model much richer metadata to produce precise, well-cited answers.

---

### 🟡 5. Better Embeddings Model (Medium Impact)

#### In [.env](file:///d:/AI_LegalSystem/.env#L27):
```diff
-EMBEDDINGS_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
-EMBEDDINGS_DIMENSIONS=2048
+EMBEDDINGS_MODEL=google/gemini-embedding-001
+EMBEDDINGS_DIMENSIONS=3072
```

> [!WARNING]
> **After changing the embeddings model, you MUST re-index all documents.** The old embeddings and new embeddings live in incompatible vector spaces. You'll need to:
> 1. Change `OPENSEARCH_CHUNKS_INDEX` to a new version (e.g., `chunks_v6`)
> 2. Re-run ingestion for all documents
> 3. Update the alias after verification

`gemini-embedding-001` significantly outperforms the Nemotron 1B model on retrieval benchmarks, especially for multilingual (Arabic+English) content.

---

### 🟢 6. Add a Relevance Score Threshold (Low-Medium Impact)

Currently, ALL retrieved chunks are passed to the LLM regardless of relevance. Low-scoring hits add noise:

#### In [chat.py](file:///d:/AI_LegalSystem/apps/api/app/routers/chat.py#L63):
```python
def _build_rag_context(req: ChatRequest) -> tuple[str, list[SearchHit]]:
    # ... existing search code ...
    
    # NEW: Filter out low-relevance hits
    if hits and hits[0].score is not None:
        max_score = hits[0].score
        # Keep only hits scoring at least 30% of the top hit
        hits = [h for h in hits if h.score and h.score >= max_score * 0.3]
    
    # ... rest of formatting ...
```

---

### 🟢 7. Add Temperature Variation for Reports (Low Impact)

Reports benefit from slightly higher temperature for more natural prose:

#### In [reports.py](file:///d:/AI_LegalSystem/apps/api/app/routers/reports.py#L90):
```diff
-            temperature=0.0
+            temperature=0.2
```

Keep chat at `0.0` for factual precision, but use `0.2` for reports to get more natural-sounding legal writing.

---

## Part 2: Switching to Native Google Gemini API

Currently your LLM calls go through OpenRouter as a proxy. Switching to the native Gemini API gives you:
- **Direct access** — no middleman, lower latency
- **Higher rate limits** — not constrained by OpenRouter free tier
- **Gemini-specific features** — thinking mode, safety settings, grounding
- **Cost efficiency** — pay Google directly instead of OpenRouter markup

### Step-by-Step Migration

#### Step 1: Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. The key will look like: `AIzaSy...`

#### Step 2: Install the Gemini SDK

Add to both [apps/api/requirements.txt](file:///d:/AI_LegalSystem/apps/api/requirements.txt) and [apps/worker/requirements.txt](file:///d:/AI_LegalSystem/apps/worker/requirements.txt):

```diff
+google-genai==1.14.0
```

#### Step 3: Update Environment Variables

Add to [.env](file:///d:/AI_LegalSystem/.env):
```env
# Gemini API (native)
GEMINI_API_KEY=AIzaSy... # Your key from Google AI Studio
GEMINI_CHAT_MODEL=gemini-2.5-flash  # or gemini-2.5-pro for max quality
```

Update [.env.example](file:///d:/AI_LegalSystem/.env.example):
```env
# Gemini API (native) — for chat/report generation
GEMINI_API_KEY=
GEMINI_CHAT_MODEL=gemini-2.5-flash
```

#### Step 4: Update Settings

In [settings.py](file:///d:/AI_LegalSystem/apps/api/app/settings.py):
```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Gemini native API (preferred for chat/reports)
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.5-flash"
    
    # Keep OpenRouter as fallback
    chat_model: str = "google/gemma-3-4b-it:free"
    chat_fallback_models: str = (
        "meta-llama/llama-3.1-8b-instruct:free,"
        "qwen/qwen2.5-7b-instruct:free"
    )
```

#### Step 5: Rewrite `llm.py` for Gemini + OpenRouter Fallback

Here's the complete rewritten [llm.py](file:///d:/AI_LegalSystem/apps/api/app/services/llm.py):

```python
"""
Generative LLM client.

Primary: Google Gemini API (native).
Fallback: OpenRouter chat completions (for free-tier / backup models).
"""

from __future__ import annotations

import logging
import os
import time

import requests

from app.settings import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Gemini native client
# ---------------------------------------------------------------------------

_gemini_client = None


def _get_gemini_client():
    """Lazy-init the Gemini client."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    
    api_key = os.getenv("GEMINI_API_KEY", settings.gemini_api_key)
    if not api_key:
        return None  # Gemini not configured; will fallback to OpenRouter
    
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except ImportError:
        logger.warning("google-genai not installed; falling back to OpenRouter")
        return None
    except Exception as exc:
        logger.warning("Failed to init Gemini client: %s", exc)
        return None


def _call_gemini(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> tuple[str, str] | None:
    """
    Try calling Gemini natively. Returns (content, model_name) or None on failure.
    """
    client = _get_gemini_client()
    if client is None:
        return None
    
    from google.genai import types
    
    model_name = model or os.getenv("GEMINI_CHAT_MODEL", settings.gemini_chat_model)
    
    # Build Gemini content format
    contents = []
    for msg in messages:
        role = msg["role"]
        # Gemini uses "user" and "model" (not "assistant")
        if role == "assistant":
            role = "model"
        elif role == "system":
            # System messages are handled via config, skip here
            continue
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    if system_prompt:
        config.system_instruction = system_prompt
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        
        text = response.text
        if not text:
            logger.warning("Gemini returned empty response")
            return None
        
        return text, model_name
    
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# OpenRouter fallback (existing logic, kept as backup)
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
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> tuple[str, str]:
    """Call OpenRouter. Raises LLMError on total failure."""
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

    last_error: str | None = None
    models = _candidate_models(model)

    for i, candidate in enumerate(models):
        payload = {
            "model": candidate,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
        except requests.RequestException as e:
            last_error = f"HTTP request failed for model {candidate}: {e}"
            continue

        if resp.status_code >= 400:
            err_msg = _parse_error(resp)
            last_error = f"OpenRouter API error on model {candidate}: {resp.status_code} {err_msg}"
            if _is_retryable_rate_limit(resp.status_code, err_msg):
                time.sleep(1.5)
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

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            last_error = f"Empty response content from model {candidate}"
            if i < len(models) - 1:
                continue
            raise LLMError(last_error)
        model_used = str(data.get("model") or candidate)
        return content, model_used

    raise LLMError(last_error or "No chat models available")


# ---------------------------------------------------------------------------
# Public API (Gemini-first, OpenRouter fallback)
# ---------------------------------------------------------------------------

def generate_chat_completion(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    content, _model_used = generate_chat_completion_with_meta(
        messages=messages,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )
    return content


def generate_chat_completion_with_meta(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
) -> tuple[str, str]:
    """
    Generate a chat completion. Tries Gemini first, falls back to OpenRouter.
    Returns (content, model_name).
    """
    # 1. Try Gemini native API first
    result = _call_gemini(
        messages=messages,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )
    if result is not None:
        return result
    
    # 2. Fallback to OpenRouter
    logger.info("Falling back to OpenRouter for chat completion")
    return _call_openrouter(
        messages=messages,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )
```

#### Step 6: Rebuild Docker Containers

```bash
docker compose build api worker
docker compose up -d
```

---

## Summary of Priority Actions

| Priority | Change | Impact | Effort |
|----------|--------|--------|--------|
| 🔴 P0 | Upgrade chat model (Gemini 2.5 Flash) | ★★★★★ | Low (config change) |
| 🔴 P0 | Improve system prompts | ★★★★☆ | Low (code change) |
| 🟡 P1 | Increase max_tokens to 4096 | ★★★☆☆ | Trivial |
| 🟡 P1 | Richer source context formatting | ★★★☆☆ | Low |
| 🟡 P1 | Switch to native Gemini API | ★★★☆☆ | Medium (new dependency) |
| 🟡 P1 | Upgrade embeddings model | ★★★☆☆ | Medium (requires reindex) |
| 🟢 P2 | Relevance threshold filtering | ★★☆☆☆ | Low |
| 🟢 P2 | Temperature tuning for reports | ★☆☆☆☆ | Trivial |

> [!TIP]
> The quickest wins are **upgrading the chat model** and **improving the prompts** — these two changes alone will dramatically improve output quality with minimal code changes. You can do both without switching to the native Gemini API (just change `CHAT_MODEL` in `.env` to `google/gemini-2.5-flash` on OpenRouter).

---

## Questions for You

1. **Budget**: Are you okay with paying for API calls? Gemini 2.5 Flash is very cheap (~$0.15/1M input tokens) but not free. If you must stay free, the prompt improvements + max_tokens increase will still help significantly.

2. **Gemini API vs OpenRouter**: Do you want me to implement the native Gemini API integration now, or would you prefer to first try upgrading the model via OpenRouter (just a `.env` change, no code needed)?

3. **Re-indexing**: Are you willing to re-ingest all documents to use the better embeddings model? This is important for search quality but requires processing time.
