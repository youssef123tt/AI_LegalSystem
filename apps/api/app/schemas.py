"""
Pydantic schemas — the shapes of data that the API sends and receives.

WHY SEPARATE FROM ORM MODELS?
------------------------------
- ORM models (models.py)  → describe database tables.
- Pydantic schemas         → describe JSON the client sees.

They are often similar, but not identical.  For example:
  - The client never sees `file_path` (an internal detail).
  - The response might combine data from multiple tables.

Keeping them separate is a widely-used best practice called
"separation of concerns" (the API layer should not leak DB details).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Response schemas (what the client receives)
# ---------------------------------------------------------------------------

class DocumentOut(BaseModel):
    """Returned after a document is created (upload response)."""
    id: uuid.UUID
    title: str
    jurisdiction: str | None = None
    year: int | None = None
    law_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
    # `from_attributes = True` tells Pydantic:
    #   "You can build this schema from a SQLAlchemy model object."
    #   Without it, Pydantic cannot read attributes like document.title.


class IngestJobOut(BaseModel):
    """Returned when the client checks job status."""
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    needs_ocr: bool | None = None
    needs_review: bool | None = None
    extraction_method: str | None = None
    quality_score: int | None = None
    arabic_letter_count: int | None = None
    arabic_presentation_forms: int | None = None
    replacement_char_count: int | None = None
    has_tounicode: bool | None = None
    indexed: bool | None = None
    indexed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Combined response from the upload endpoint."""
    document: DocumentOut
    job: IngestJobOut


# ---------------------------------------------------------------------------
# Milestone 3 schemas (chunks + search)
# ---------------------------------------------------------------------------


class ChunkOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    ordinal: int
    section_path: list[str] | None = None
    page_start: int | None = None
    page_end: int | None = None
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchFilters(BaseModel):
    jurisdiction: str | None = None
    law_type: str | None = None
    year_min: int | None = None
    year_max: int | None = None


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters | None = None
    top_k: int = 10
    mode: str | None = None  # "keyword" | "vector" | "hybrid"
    keyword_weight: float | None = None
    vector_weight: float | None = None


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None = None
    section_path: list[str] = []
    ordinal: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    score: float | None = None
    snippet: str
    jurisdiction: str | None = None
    year: int | None = None
    law_type: str | None = None
    source: str | None = None
    citations: list[str] = []
    citation_types: list[str] = []
    citation_official_urls: list[str] = []


class SearchResponse(BaseModel):
    index: str
    hits: list[SearchHit]


class CitationOut(BaseModel):
    canonical_id: str
    citation_type: str
    jurisdiction: str | None = None
    display: str | None = None
    official_url: str | None = None


class SectionOutlineItem(BaseModel):
    path: list[str]
    chunk_count: int
    first_ordinal: int


# ---------------------------------------------------------------------------
# Milestone 7: Chat and Reports
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    filters: SearchFilters | None = None
    top_k: int = 15
    mode: str | None = None  # "keyword" | "vector" | "hybrid"
    llm_provider: str | None = None  # "openrouter" | "gemini"
    llm_model: str | None = None
    max_tokens: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SearchHit]
    model_used: str | None = None
    provider_used: str | None = None


class ReportRequest(BaseModel):
    query: str
    filters: SearchFilters | None = None
    top_k: int = 25
    mode: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    max_tokens: int | None = None


class ReportResponse(BaseModel):
    report: str
    sources: list[SearchHit]
    model_used: str | None = None
    provider_used: str | None = None


class AuditCitation(BaseModel):
    canonical_id: str
    citation_type: str
    jurisdiction: str | None = None
    display: str | None = None
    official_url: str | None = None
    raw_text: str | None = None
    start_char: int | None = None
    end_char: int | None = None


class AuditSource(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None = None
    section_path: list[str] = []
    ordinal: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    snippet: str
    jurisdiction: str | None = None
    year: int | None = None
    law_type: str | None = None
    source: str | None = None
    citations: list[AuditCitation] = []


class AuditExportRequest(BaseModel):
    query: str
    filters: SearchFilters | None = None
    top_k: int = 10
    mode: str | None = None


class AuditExportResponse(BaseModel):
    index: str
    query: str
    mode: str
    sources_used: list[AuditSource]
