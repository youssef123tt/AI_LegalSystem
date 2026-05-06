"""
Central configuration for the API service.

HOW IT WORKS
------------
Pydantic-Settings reads environment variables (and the .env file) and
maps them to typed Python attributes.  If the env var `UPLOAD_DIR` is set,
settings.upload_dir will have that value; otherwise it uses the default.

This means the same code works locally AND in Docker — just change env vars.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_name: str = "ai-legal-knowledge-assistant"

    database_url: str = "postgresql+psycopg://legal:legal@localhost:5432/legal_rag"
    redis_url: str = "redis://localhost:6379/0"
    opensearch_url: str = "http://localhost:9200"

    # NEW in Milestone 2: where uploaded files are stored.
    upload_dir: str = "/data/uploads"

    # Milestone 3: OpenSearch keyword index for chunks.
    # NOTE: We version OpenSearch indexes because mappings evolve.
    # `chunks_v2` adds Arabic/English analyzed subfields for better multilingual search.
    opensearch_chunks_index: str = "chunks_v3"
    # Stable alias clients should search against (optional; can be enabled later).
    opensearch_chunks_alias: str = "chunks_current"
    opensearch_init_on_startup: bool = False

    # Milestone 7: embeddings (OpenRouter).
    embeddings_base_url: str = "https://openrouter.ai/api/v1"
    embeddings_model: str = "google/gemini-embedding-001"
    embeddings_dimensions: int = 3072

    # Chat / Generative LLM (env: CHAT_MODEL)
    chat_model: str = "google/gemma-3-4b-it:free"
    chat_max_tokens: int = 4096
    # Primary provider for chat/report generation when request does not specify one.
    llm_provider_default: str = "openrouter"

    # Native Gemini API (optional)
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_chat_model: str = "gemini-2.5-flash"

    # Comma-separated fallback chat models (env: CHAT_FALLBACK_MODELS).
    chat_fallback_models: str = (
        "meta-llama/llama-3.1-8b-instruct:free,"
        "openrouter/free"
    )


settings = Settings()
