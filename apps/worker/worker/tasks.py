"""
Celery task: process_document.

Milestone 3 implementation:
- Extract text from uploaded file (PDF/DOCX/TXT; no OCR yet)
- Normalize text
- Store full extracted text snapshot (document_texts)
- Chunk text (basic chunking)
- Store chunks in Postgres
- Index chunks into OpenSearch (keyword/BM25)

Milestone 4 adds OCR for scanned PDFs.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from sqlalchemy import select

from shared.chunking import chunk_text_basic
from shared.citations import extract_citations
from shared.database import SessionLocal
from shared.extraction import (
    ExtractionError,
    extract_text_with_metadata,
    audit_pdf_tounicode,
    quality_score_for_text,
    extract_pdf_ocr_with_metrics,
)
from shared.models import Chunk, Document, DocumentText, IngestJob, Citation, ChunkCitation, CitationEdge
from shared.opensearch_index import chunks_v1_keyword_index_body, chunks_v3_hybrid_index_body
from shared.section_chunking import SectionChunk, chunk_text_section_aware
from shared.embeddings import embed_texts
from shared.text_utils import normalize_text
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _db():
    return SessionLocal()


def _opensearch_client() -> OpenSearch:
    url = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    return OpenSearch(hosts=[url])

def _chunks_index_name() -> str:
    return os.getenv("OPENSEARCH_CHUNKS_INDEX", "chunks_v3")


def _ensure_chunks_index(client: OpenSearch) -> None:
    index = _chunks_index_name()
    if client.indices.exists(index=index):
        return
        
    if "v3" in index:
        body = chunks_v3_hybrid_index_body(
            embedding_dim=int(os.getenv("EMBEDDINGS_DIMENSIONS", "3072"))
        )
    else:
        body = chunks_v1_keyword_index_body()
        
    client.indices.create(index=index, body=body)


def _normalize_page_map(page_map: dict | None) -> dict | None:
    if not page_map or "pages" not in page_map:
        return page_map
    out_pages: list[dict] = []
    cursor = 0
    pages = page_map.get("pages") or []
    for p in pages:
        text = p.get("text")
        if text is None:
            # We only need offsets and page IDs; keep existing values if no text present.
            out_pages.append(
                {
                    "page": int(p.get("page")),
                    "char_start": int(p.get("char_start", 0)),
                    "char_end": int(p.get("char_end", 0)),
                    "char_count": int(p.get("char_count", 0)),
                }
            )
            continue
        start = cursor
        cursor += len(text)
        out_pages.append(
            {
                "page": int(p.get("page")),
                "char_start": start,
                "char_end": cursor,
                "char_count": len(text),
            }
        )
        cursor += 2
    return {"pages": out_pages}


def _assign_chunk_offsets_and_pages(chunk_rows: list[Chunk], full_text: str, page_map_json: dict | None) -> None:
    pages = (page_map_json or {}).get("pages", [])
    cursor = 0
    for ch in chunk_rows:
        idx = full_text.find(ch.text, max(0, cursor - 2000))
        if idx < 0:
            # Fallback: use prefix matching for overlapped chunks.
            needle = ch.text[:120]
            if needle:
                idx = full_text.find(needle, max(0, cursor - 4000))
        if idx < 0:
            continue

        end = idx + len(ch.text)
        ch.char_start = idx
        ch.char_end = end
        cursor = idx

        overlapped_pages: list[int] = []
        for p in pages:
            ps = int(p.get("char_start", 0))
            pe = int(p.get("char_end", 0))
            if end <= ps or idx >= pe:
                continue
            overlapped_pages.append(int(p.get("page")))
        if overlapped_pages:
            ch.page_start = min(overlapped_pages)
            ch.page_end = max(overlapped_pages)


@celery_app.task(name="worker.tasks.process_document", bind=True)
def process_document(self, job_id: str):
    """
    Process an ingested document.

    Parameters
    ----------
    job_id : str
        UUID of the IngestJob to process (passed as string because UUIDs
        aren't JSON-serializable by default).
    """
    logger.info("Starting process_document for job_id=%s", job_id)

    db = _db()
    job: IngestJob | None = None
    try:
        job = db.query(IngestJob).filter(IngestJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error("Job %s not found in database", job_id)
            return

        doc = db.query(Document).filter(Document.id == job.document_id).first()
        if not doc:
            raise RuntimeError(f"Document {job.document_id} not found")
        if not doc.file_path:
            raise RuntimeError(f"Document {doc.id} has no file_path")

        job.status = "processing"
        job.updated_at = datetime.now(timezone.utc)
        # Reset diagnostics for retries.
        if hasattr(job, "needs_ocr"):
            job.needs_ocr = False
        if hasattr(job, "needs_review"):
            job.needs_review = False
        if hasattr(job, "indexed"):
            job.indexed = False
        if hasattr(job, "indexed_at"):
            job.indexed_at = None
        if hasattr(job, "error_message"):
            job.error_message = None
        db.commit()

        # 1) Audit PDF encoding risk (best-effort).
        has_tounicode = None
        if doc.file_path.lower().endswith(".pdf"):
            has_tounicode = audit_pdf_tounicode(doc.file_path)

        # 2) Extract text (no OCR in Milestone 3).
        try:
            raw_text, method, page_map_json = extract_text_with_metadata(doc.file_path)
        except ExtractionError as exc:
            raise RuntimeError(str(exc)) from exc

        text = normalize_text(raw_text)
        # Store extraction method/diagnostics on the job (if columns exist).
        if hasattr(job, "extraction_method"):
            job.extraction_method = method
        if hasattr(job, "has_tounicode"):
            job.has_tounicode = has_tounicode

        # Quality metrics (useful for Arabic).
        pres_a = sum(1 for ch in text if "\uFB50" <= ch <= "\uFDFF")
        pres_b = sum(1 for ch in text if "\uFE70" <= ch <= "\uFEFF")
        arabic_letters = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
        replacement_chars = text.count("\ufffd")
        presentation_forms = pres_a + pres_b

        if hasattr(job, "quality_score"):
            job.quality_score = quality_score_for_text(text)
        if hasattr(job, "arabic_letter_count"):
            job.arabic_letter_count = arabic_letters
        if hasattr(job, "arabic_presentation_forms"):
            job.arabic_presentation_forms = presentation_forms
        if hasattr(job, "replacement_char_count"):
            job.replacement_char_count = replacement_chars

        db.commit()

        if len(text) < 200 and doc.file_path.lower().endswith(".pdf"):
            # Likely scanned or extraction-poor PDF. Fallback to OCR.
            logger.info("Text length < 200 for PDF job %s, falling back to OCR", job_id)
            try:
                raw_text, ocr_metrics = extract_pdf_ocr_with_metrics(doc.file_path)
                text = normalize_text(raw_text)
                method = "pdf_ocr"
                page_map_json = ocr_metrics.get("page_map")
                if hasattr(job, "extraction_method"):
                    job.extraction_method = method
                low_conf_threshold = float(os.getenv("OCR_CONFIDENCE_MIN", "60"))
                if hasattr(job, "needs_review") and float(ocr_metrics.get("avg_confidence", 0)) < low_conf_threshold:
                    job.needs_review = True
                    job.error_message = (
                        f"Low OCR confidence ({ocr_metrics.get('avg_confidence')}) below {low_conf_threshold}."
                    )
            except Exception as e:
                logger.error("OCR failed for job %s: %s", job_id, e)
                job.status = "needs_ocr"
                if hasattr(job, "needs_ocr"):
                    job.needs_ocr = True
                job.error_message = f"OCR failed: {e}"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                return

        # Check quality after potential OCR or normal extraction
        # Recalculate metrics in case we did OCR
        pres_a = sum(1 for ch in text if "\uFB50" <= ch <= "\uFDFF")
        pres_b = sum(1 for ch in text if "\uFE70" <= ch <= "\uFEFF")
        presentation_forms = pres_a + pres_b

        # If Arabic extraction still looks "glyph-shaped" after normalization,
        # treat it similarly to scanned PDFs (OCR will usually fix this).
        if presentation_forms > 50 and method != "pdf_ocr" and doc.file_path.lower().endswith(".pdf"):
            logger.info("presentation_forms > 50 for job %s, falling back to OCR", job_id)
            try:
                raw_text, ocr_metrics = extract_pdf_ocr_with_metrics(doc.file_path)
                text = normalize_text(raw_text)
                method = "pdf_ocr"
                page_map_json = ocr_metrics.get("page_map")
                if hasattr(job, "extraction_method"):
                    job.extraction_method = method
                low_conf_threshold = float(os.getenv("OCR_CONFIDENCE_MIN", "60"))
                if hasattr(job, "needs_review") and float(ocr_metrics.get("avg_confidence", 0)) < low_conf_threshold:
                    job.needs_review = True
                    job.error_message = (
                        f"Low OCR confidence ({ocr_metrics.get('avg_confidence')}) below {low_conf_threshold}."
                    )
                # Recalculate metrics to see if it improved and for needs_review
                pres_a = sum(1 for ch in text if "\uFB50" <= ch <= "\uFDFF")
                pres_b = sum(1 for ch in text if "\uFE70" <= ch <= "\uFEFF")
                presentation_forms = pres_a + pres_b
            except Exception as e:
                logger.error("OCR fallback failed for job %s: %s", job_id, e)
                job.status = "needs_ocr"
                if hasattr(job, "needs_ocr"):
                    job.needs_ocr = True
                job.error_message = (
                    "Arabic PDF text extraction produced many presentation-form glyphs. "
                    f"OCR fallback failed: {e}"
                )
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                return

        # Update metrics again in db after potential OCR
        arabic_letters = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
        replacement_chars = text.count("\ufffd")
        if hasattr(job, "quality_score"):
            job.quality_score = quality_score_for_text(text)
        if hasattr(job, "arabic_letter_count"):
            job.arabic_letter_count = arabic_letters
        if hasattr(job, "arabic_presentation_forms"):
            job.arabic_presentation_forms = presentation_forms
        if hasattr(job, "replacement_char_count"):
            job.replacement_char_count = replacement_chars

        # Mark marginal cases for review (but still index).
        if hasattr(job, "needs_review"):
            if has_tounicode is False and arabic_letters > 200:
                job.needs_review = True
            if presentation_forms > 0 and arabic_letters > 0:
                job.needs_review = True
            if replacement_chars > 0:
                job.needs_review = True
            db.commit()

        # 2) Idempotency for retries: remove old derived rows.
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        db.query(DocumentText).filter(DocumentText.document_id == doc.id).delete()
        db.commit()

        # 3) Store full extracted text snapshot.
        db.add(
            DocumentText(
                document_id=doc.id,
                extraction_method=method,
                text=text,
                page_map_json=_normalize_page_map(page_map_json),
            )
        )
        db.commit()

        # 4) Chunk the text (section-aware in Milestone 6; falls back to basic).
        section_chunks = chunk_text_section_aware(text, max_chars=2000, overlap_chars=200)
        if not section_chunks:
            # Fallback to basic chunker if we can't detect headings.
            pieces = chunk_text_basic(text, max_chars=2000, overlap_chars=200)
            section_chunks = [SectionChunk(ordinal=p.ordinal, text=p.text, section_path=[]) for p in pieces]

        if not section_chunks:
            raise RuntimeError("Chunking produced zero chunks")

        chunk_rows: list[Chunk] = []
        for piece in section_chunks:
            chunk_rows.append(
                Chunk(
                    document_id=doc.id,
                    ordinal=piece.ordinal,
                    section_path=piece.section_path,
                    text=piece.text,
                    char_start=None,
                    char_end=None,
                    token_count=None,
                    embedding_model=os.getenv("EMBEDDINGS_MODEL", "google/gemini-embedding-001"),
                    embedded_at=None,
                )
            )
        db.add_all(chunk_rows)
        _assign_chunk_offsets_and_pages(chunk_rows, text, _normalize_page_map(page_map_json))
        db.commit()

        # 5) Citation extraction + linking (Milestone 5).
        # Idempotency: remove previous edges/mentions for this document.
        chunk_ids_subq = select(Chunk.id).where(Chunk.document_id == doc.id)
        db.query(ChunkCitation).filter(ChunkCitation.chunk_id.in_(chunk_ids_subq)).delete(synchronize_session=False)
        db.query(CitationEdge).filter(CitationEdge.from_document_id == doc.id).delete(synchronize_session=False)
        db.commit()

        chunk_citations_map: dict[uuid.UUID, list[str]] = {}
        chunk_citation_types_map: dict[uuid.UUID, list[str]] = {}
        chunk_citation_urls_map: dict[uuid.UUID, list[str]] = {}
        doc_citation_ids: set[uuid.UUID] = set()

        for ch in chunk_rows:
            matches = extract_citations(ch.text, default_jurisdiction=doc.jurisdiction)
            if not matches:
                continue

            canonical_ids_for_chunk: list[str] = []
            types_for_chunk: list[str] = []
            urls_for_chunk: list[str] = []

            for m in matches:
                cit = db.query(Citation).filter(Citation.canonical_id == m.canonical_id).first()
                if not cit:
                    cit = Citation(
                        canonical_id=m.canonical_id,
                        citation_type=m.citation_type,
                        jurisdiction=m.jurisdiction,
                        display=m.display or m.raw_text,
                        official_url=m.official_url,
                    )
                    db.add(cit)
                    db.flush()
                elif m.official_url and not cit.official_url:
                    cit.official_url = m.official_url

                db.add(
                    ChunkCitation(
                        chunk_id=ch.id,
                        citation_id=cit.id,
                        raw_text=m.raw_text[:500],
                        start_char=m.start_char,
                        end_char=m.end_char,
                    )
                )

                canonical_ids_for_chunk.append(cit.canonical_id)
                types_for_chunk.append(cit.citation_type)
                if cit.official_url:
                    urls_for_chunk.append(cit.official_url)
                doc_citation_ids.add(cit.id)

            chunk_citations_map[ch.id] = sorted(set(canonical_ids_for_chunk))
            chunk_citation_types_map[ch.id] = sorted(set(types_for_chunk))
            chunk_citation_urls_map[ch.id] = sorted(set(urls_for_chunk))

        # Add edges: document -> citation (unique).
        for cit_id in doc_citation_ids:
            db.add(CitationEdge(from_document_id=doc.id, to_citation_id=cit_id))

        db.commit()

        # 6) Embeddings (Milestone 7 Part 1): compute vectors for chunks.
        vectors = embed_texts([c.text for c in chunk_rows])
        now = datetime.now(timezone.utc)
        for c in chunk_rows:
            c.embedded_at = now
        db.commit()

        # 7) Index chunks into OpenSearch (keyword + citations + vectors).
        client = _opensearch_client()
        _ensure_chunks_index(client)
        index = _chunks_index_name()

        actions = []
        for ch, vec in zip(chunk_rows, vectors, strict=False):
            actions.append(
                {
                    "_op_type": "index",
                    "_index": index,
                    "_id": str(ch.id),
                    "_source": {
                        "chunk_id": str(ch.id),
                        "document_id": str(doc.id),
                        "document_title": doc.title,
                        "text": ch.text,
                        "citations": chunk_citations_map.get(ch.id, []),
                        "citation_types": chunk_citation_types_map.get(ch.id, []),
                        "citation_official_urls": chunk_citation_urls_map.get(ch.id, []),
                        "embedding": vec,
                        "jurisdiction": doc.jurisdiction,
                        "year": doc.year,
                        "law_type": doc.law_type,
                        "source": doc.source_url or "upload",
                        "section_path": ch.section_path or [],
                        "ordinal": ch.ordinal,
                        "page_start": ch.page_start,
                        "page_end": ch.page_end,
                    },
                }
            )

        bulk(client, actions, refresh=True)

        job.status = "complete"
        if hasattr(job, "indexed"):
            job.indexed = True
        if hasattr(job, "indexed_at"):
            job.indexed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        try:
            if job is None:
                job = db.query(IngestJob).filter(IngestJob.id == uuid.UUID(job_id)).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.exception("Could not update job %s to failed status", job_id)
    finally:
        db.close()
