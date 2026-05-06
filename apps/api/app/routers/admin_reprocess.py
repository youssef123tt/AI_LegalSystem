"""
Admin endpoints to re-run ingestion without re-uploading.

This is useful when:
- extraction logic changes
- OpenSearch mapping/index version changes
- you want to re-chunk/re-index a document
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.settings import settings
from shared.database import get_db
from shared.models import Document, IngestJob
from celery import Celery


def _celery_app() -> Celery:
    return Celery("legal_rag_worker", broker=settings.redis_url)


router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/documents/{document_id}/reprocess")
def reprocess_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Create a new ingest job for an existing document and enqueue it.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path:
        raise HTTPException(status_code=400, detail="Document has no file_path")

    job = IngestJob(document_id=doc.id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    celery = _celery_app()
    celery.send_task("worker.tasks.process_document", args=[str(job.id)])

    return {"document_id": str(doc.id), "job_id": str(job.id), "status": job.status}

