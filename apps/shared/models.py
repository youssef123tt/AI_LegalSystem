"""
SQLAlchemy ORM models — the Python classes that map to Postgres tables.

HOW IT WORKS
------------
1.  You define a class that inherits from `Base`.
2.  You set `__tablename__` to the actual table name in Postgres.
3.  Each class attribute that uses `mapped_column(...)` becomes a column.
4.  Alembic reads these classes and generates migration SQL automatically.

TABLES CREATED IN MILESTONE 2
------------------------------
- documents   : one row per uploaded legal document (law, regulation, etc.).
- ingest_jobs : one row per background-processing job (tracks queued → complete).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base class — every model inherits from this.
# Alembic's env.py imports Base.metadata to know which tables should exist.
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Document — metadata for one legal document.
# ---------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    # Primary key: UUID generated in Python (not auto-increment integer).
    # UUIDs are better for distributed systems because two servers will
    # never accidentally generate the same ID.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Legal metadata — used later for filtering searches.
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer)
    law_type: Mapped[str | None] = mapped_column(String(50))

    # Where the raw file lives on disk (or S3 later).
    file_path: Mapped[str | None] = mapped_column(String(1000))

    # Optional URL where the document was originally found.
    source_url: Mapped[str | None] = mapped_column(String(2000))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationship: one document can have many ingest jobs (e.g., retries).
    # `back_populates` tells SQLAlchemy that IngestJob.document points back here.
    jobs: Mapped[list["IngestJob"]] = relationship(back_populates="document")

    # Milestone 3: extracted text and chunks.
    texts: Mapped[list["DocumentText"]] = relationship(back_populates="document")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
    citation_edges: Mapped[list["CitationEdge"]] = relationship(back_populates="from_document")

    def __repr__(self) -> str:
        return f"<Document {self.id} title={self.title!r}>"


# ---------------------------------------------------------------------------
# IngestJob — tracks one background-processing run for a document.
# ---------------------------------------------------------------------------
class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign key → documents.id
    # This links each job to the document it processes.
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    # Status as a simple string: queued | processing | complete | failed
    # (A Postgres ENUM could also work, but plain strings are simpler to
    #  evolve — you just start writing a new value.)
    status: Mapped[str] = mapped_column(String(20), default="queued")

    # Milestone 3+: extraction diagnostics / routing flags.
    # These keep "complete but suspicious" separate from "failed".
    needs_ocr: Mapped[bool] = mapped_column(default=False)
    needs_review: Mapped[bool] = mapped_column(default=False)

    extraction_method: Mapped[str | None] = mapped_column(String(50))
    quality_score: Mapped[int | None] = mapped_column(Integer)
    arabic_letter_count: Mapped[int | None] = mapped_column(Integer)
    arabic_presentation_forms: Mapped[int | None] = mapped_column(Integer)
    replacement_char_count: Mapped[int | None] = mapped_column(Integer)
    has_tounicode: Mapped[bool | None] = mapped_column(nullable=True)

    indexed: Mapped[bool] = mapped_column(default=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # If the job failed, store the error message for debugging.
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to Document.
    document: Mapped["Document"] = relationship(back_populates="jobs")

    def __repr__(self) -> str:
        return f"<IngestJob {self.id} status={self.status}>"


# ---------------------------------------------------------------------------
# DocumentText - full extracted text snapshot for a document.
# (Useful for debugging and future re-chunking without re-parsing the file.)
# ---------------------------------------------------------------------------
class DocumentText(Base):
    __tablename__ = "document_texts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    # Example values: "pdf_text", "docx_text", "ocr_text" (OCR comes in M4).
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)

    # Full extracted text. (Could later be replaced by an object-storage key.)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: helps later when we want to map chunk offsets back to pages.
    page_map_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="texts")

    def __repr__(self) -> str:
        return f"<DocumentText {self.id} document_id={self.document_id}>"


# ---------------------------------------------------------------------------
# Chunk - the unit of search/retrieval (keyword now, vectors later).
# ---------------------------------------------------------------------------
class Chunk(Base):
    __tablename__ = "chunks"
          
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    # Ordering within the document (0,1,2...).
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    # Milestone 3: placeholder. Milestone 6 will populate real structure.
    # Stored as JSON array of strings, e.g. ["Article 3", "Clause 2"].
    section_path: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional offsets into the full extracted text (if we store it).
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Optional approximation. (We can fill this later when we tokenize.)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Milestone 7: embedding metadata (vector lives in OpenSearch).
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")
    citations: Mapped[list["ChunkCitation"]] = relationship(back_populates="chunk")

    def __repr__(self) -> str:
        return f"<Chunk {self.id} document_id={self.document_id} ordinal={self.ordinal}>"


# ---------------------------------------------------------------------------
# Citation - normalized citation reference (statute/case/law/etc.)
# ---------------------------------------------------------------------------
class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Canonical identifier, e.g. "us:usc:18:1030" or "eg:law:2025:14".
    canonical_id: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)

    # Simple category: "usc", "cfr", "case", "eg_law", "article_ref", ...
    citation_type: Mapped[str] = mapped_column(String(50), nullable=False)

    jurisdiction: Mapped[str | None] = mapped_column(String(50))
    display: Mapped[str | None] = mapped_column(String(500))
    official_url: Mapped[str | None] = mapped_column(String(2000))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    chunk_mentions: Mapped[list["ChunkCitation"]] = relationship(back_populates="citation")
    incoming_edges: Mapped[list["CitationEdge"]] = relationship(back_populates="to_citation")

    def __repr__(self) -> str:
        return f"<Citation {self.canonical_id}>"


# ---------------------------------------------------------------------------
# ChunkCitation - occurrence of a citation within a specific chunk
# ---------------------------------------------------------------------------
class ChunkCitation(Base):
    __tablename__ = "chunk_citations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chunks.id"),
        nullable=False,
    )
    citation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citations.id"),
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(String(500), nullable=False)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    chunk: Mapped["Chunk"] = relationship(back_populates="citations")
    citation: Mapped["Citation"] = relationship(back_populates="chunk_mentions")

    def __repr__(self) -> str:
        return f"<ChunkCitation chunk_id={self.chunk_id} citation_id={self.citation_id}>"


# ---------------------------------------------------------------------------
# CitationEdge - graph foundation: a document cites a citation
# ---------------------------------------------------------------------------
class CitationEdge(Base):
    __tablename__ = "citation_edges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    from_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )
    to_citation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citations.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    from_document: Mapped["Document"] = relationship(back_populates="citation_edges")
    to_citation: Mapped["Citation"] = relationship(back_populates="incoming_edges")

    def __repr__(self) -> str:
        return f"<CitationEdge from={self.from_document_id} to={self.to_citation_id}>"
