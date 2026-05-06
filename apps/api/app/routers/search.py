"""
Milestone 3 search + chunk listing endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from opensearchpy import OpenSearch
from opensearchpy.exceptions import RequestError
from sqlalchemy.orm import Session

from app.schemas import ChunkOut, SearchRequest, SearchResponse, SearchHit, CitationOut, SectionOutlineItem
from app.settings import settings
from shared.embeddings import embed_one
from shared.database import get_db
from shared.models import Chunk, Citation, ChunkCitation


router = APIRouter(prefix="/v1", tags=["search"])


def _client() -> OpenSearch:
    return OpenSearch(hosts=[settings.opensearch_url])


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkOut])
def list_document_chunks(
    document_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List chunks for a document from Postgres (source of truth).
    """
    q = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.ordinal.asc())
        .limit(limit)
        .offset(offset)
    )
    return [ChunkOut.model_validate(row) for row in q.all()]


@router.get("/documents/{document_id}/outline", response_model=list[SectionOutlineItem])
def get_document_outline(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Return a simple section outline derived from stored chunk.section_path.

    The result is ordered by first occurrence in the document.
    """
    rows = (
        db.query(Chunk.ordinal, Chunk.section_path)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.ordinal.asc())
        .all()
    )

    # Use tuple(section_path) as key; preserve first occurrence order.
    stats: dict[tuple[str, ...], dict] = {}
    for ordinal, section_path in rows:
        path_list = section_path or []
        key = tuple(path_list)
        if key not in stats:
            stats[key] = {"chunk_count": 0, "first_ordinal": int(ordinal)}
        stats[key]["chunk_count"] += 1

    out: list[SectionOutlineItem] = []
    for key, v in sorted(stats.items(), key=lambda kv: kv[1]["first_ordinal"]):
        out.append(
            SectionOutlineItem(
                path=list(key),
                chunk_count=int(v["chunk_count"]),
                first_ordinal=int(v["first_ordinal"]),
            )
        )
    return out


@router.get("/documents/{document_id}/citations", response_model=list[CitationOut])
def list_document_citations(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    List unique citations mentioned in a document (via its chunks).
    """
    rows = (
        db.query(Citation)
        .join(ChunkCitation, ChunkCitation.citation_id == Citation.id)
        .join(Chunk, Chunk.id == ChunkCitation.chunk_id)
        .filter(Chunk.document_id == document_id)
        .distinct(Citation.id)
        .all()
    )
    return [
        CitationOut(
            canonical_id=r.canonical_id,
            citation_type=r.citation_type,
            jurisdiction=r.jurisdiction,
            display=r.display,
            official_url=r.official_url,
        )
        for r in rows
    ]


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Keyword-only search (BM25) in Milestone 3.

    Later milestones will add embeddings + hybrid scoring.
    """
    client = _client()
    # Prefer alias so we can reindex safely (falls back to index if alias not set up).
    index = settings.opensearch_chunks_alias or settings.opensearch_chunks_index

    mode = getattr(req, "mode", None) or "hybrid"
    keyword_weight = float(getattr(req, "keyword_weight", 1.0) or 1.0)
    vector_weight = float(getattr(req, "vector_weight", 1.0) or 1.0)

    keyword_query = {
        "multi_match": {
            "query": req.query,
            "fields": ["text", "text.en", "text.ar", "document_title"],
            "type": "best_fields",
        }
    }
    filters = []

    if req.filters:
        if req.filters.jurisdiction:
            filters.append({"term": {"jurisdiction": req.filters.jurisdiction}})
        if req.filters.law_type:
            filters.append({"term": {"law_type": req.filters.law_type}})
        if req.filters.year_min is not None or req.filters.year_max is not None:
            rng: dict = {}
            if req.filters.year_min is not None:
                rng["gte"] = req.filters.year_min
            if req.filters.year_max is not None:
                rng["lte"] = req.filters.year_max
            filters.append({"range": {"year": rng}})

    size = max(1, min(req.top_k, 50))

    # Vector query is only available if the index has knn_vector field.
    vector_clause = None
    if mode in ("vector", "hybrid"):
        qvec = embed_one(req.query)
        vector_clause = {
            "knn": {
                "embedding": {
                    "vector": qvec,
                    "k": size,
                }
            }
        }

    if mode == "keyword":
        query = {"bool": {"must": [keyword_query], "filter": filters}}
    elif mode == "vector":
        if not vector_clause:
            query = {"bool": {"must": [keyword_query], "filter": filters}}
        else:
            query = {"bool": {"must": [vector_clause], "filter": filters}}
    else:
        # Hybrid: combine keyword + vector as should clauses.
        should = []
        should.append({"bool": {"must": [keyword_query], "boost": keyword_weight}})
        if vector_clause:
            should.append({"bool": {"must": [vector_clause], "boost": vector_weight}})
        query = {"bool": {"should": should, "minimum_should_match": 1, "filter": filters}}

    body = {"size": size, "query": query, "highlight": {"fields": {"text": {}}}}

    try:
        resp = client.search(index=index, body=body)
    except RequestError as exc:
        msg = str(exc)
        # Graceful fallback when index has no knn_vector mapping yet.
        if mode in ("hybrid", "vector") and "not knn_vector type" in msg:
            query = {"bool": {"must": [keyword_query], "filter": filters}}
            body = {"size": size, "query": query, "highlight": {"fields": {"text": {}}}}
            resp = client.search(index=index, body=body)
        else:
            raise
    hits = resp.get("hits", {}).get("hits", [])

    out_hits: list[SearchHit] = []
    for h in hits:
        src = h.get("_source", {}) or {}
        hl = h.get("highlight", {}) or {}
        snippet = ""
        if "text" in hl and hl["text"]:
            snippet = " ... ".join(hl["text"])
        else:
            snippet = (src.get("text") or "")[:400]

        out_hits.append(
            SearchHit(
                chunk_id=str(src.get("chunk_id") or h.get("_id")),
                document_id=str(src.get("document_id") or ""),
                document_title=src.get("document_title"),
                section_path=src.get("section_path") or [],
                ordinal=src.get("ordinal"),
                page_start=src.get("page_start"),
                page_end=src.get("page_end"),
                score=h.get("_score"),
                snippet=snippet,
                jurisdiction=src.get("jurisdiction"),
                year=src.get("year"),
                law_type=src.get("law_type"),
                source=src.get("source"),
                citations=src.get("citations") or [],
                citation_types=src.get("citation_types") or [],
                citation_official_urls=src.get("citation_official_urls") or [],
            )
        )

    return SearchResponse(index=index, hits=out_hits)
