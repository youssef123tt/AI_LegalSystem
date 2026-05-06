from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas import (
    AuditExportRequest,
    AuditExportResponse,
    AuditSource,
    AuditCitation,
    SearchRequest,
)
from app.routers.search import search as run_search
from shared.database import get_db
from shared.models import ChunkCitation, Citation, Chunk


router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.post("/sources", response_model=AuditExportResponse)
def export_sources_used(req: AuditExportRequest, db: Session = Depends(get_db)):
    mode = req.mode or "hybrid"
    search_req = SearchRequest(
        query=req.query,
        filters=req.filters,
        top_k=req.top_k,
        mode=mode,
    )
    search_resp = run_search(search_req)

    chunk_ids: list[uuid.UUID] = []
    for h in search_resp.hits:
        try:
            chunk_ids.append(uuid.UUID(h.chunk_id))
        except Exception:
            continue

    citation_map: dict[uuid.UUID, list[AuditCitation]] = {}
    if chunk_ids:
        rows = (
            db.query(ChunkCitation, Citation)
            .join(Citation, Citation.id == ChunkCitation.citation_id)
            .filter(ChunkCitation.chunk_id.in_(chunk_ids))
            .all()
        )
        for cc, c in rows:
            citation_map.setdefault(cc.chunk_id, []).append(
                AuditCitation(
                    canonical_id=c.canonical_id,
                    citation_type=c.citation_type,
                    jurisdiction=c.jurisdiction,
                    display=c.display,
                    official_url=c.official_url,
                    raw_text=cc.raw_text,
                    start_char=cc.start_char,
                    end_char=cc.end_char,
                )
            )

    # Enrich page mapping from DB when index docs are older and don't include page fields yet.
    page_map: dict[uuid.UUID, tuple[int | None, int | None]] = {}
    if chunk_ids:
        for cid, p1, p2 in db.query(Chunk.id, Chunk.page_start, Chunk.page_end).filter(Chunk.id.in_(chunk_ids)).all():
            page_map[cid] = (p1, p2)

    sources: list[AuditSource] = []
    for h in search_resp.hits:
        try:
            cid = uuid.UUID(h.chunk_id)
        except Exception:
            cid = None
        pages = page_map.get(cid) if cid else None
        page_start = h.page_start if h.page_start is not None else (pages[0] if pages else None)
        page_end = h.page_end if h.page_end is not None else (pages[1] if pages else None)
        sources.append(
            AuditSource(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                section_path=h.section_path,
                ordinal=h.ordinal,
                page_start=page_start,
                page_end=page_end,
                snippet=h.snippet,
                jurisdiction=h.jurisdiction,
                year=h.year,
                law_type=h.law_type,
                source=h.source,
                citations=citation_map.get(cid, []),
            )
        )

    return AuditExportResponse(
        index=search_resp.index,
        query=req.query,
        mode=mode,
        sources_used=sources,
    )

