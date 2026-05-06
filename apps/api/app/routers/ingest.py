"""
Ingest router — handles document uploads and job status checks.

ENDPOINTS
---------
POST /v1/documents/upload   — Upload a legal document file + metadata.
GET  /v1/jobs/{job_id}      — Check the status of a background ingest job.

HOW THE UPLOAD FLOW WORKS
-------------------------
1. Client sends a file (PDF, DOCX, TXT …) plus metadata fields via a
   multipart form (this is standard HTTP file upload).
2. The API saves the raw file to disk under UPLOAD_DIR.
3. The API creates a `Document` row in Postgres.
4. The API creates an `IngestJob` row with status="queued".
5. The API sends a Celery task to the Redis queue.
6. The API returns the document + job to the client immediately (fast!).
7. In the background, the Worker picks up the task and processes the file.
"""

import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.settings import settings
from app.schemas import DocumentOut, IngestJobOut, UploadResponse
from shared.database import get_db
from shared.models import Document, IngestJob

# We import the Celery app so we can send tasks to the queue.
# `send_task` lets us fire a task by name without importing the task function
# (the task function lives in the Worker service, not the API).
from celery import Celery


def _celery_app() -> Celery:
    """Create a lightweight Celery client just for sending tasks."""
    return Celery(
        "legal_rag_worker",
        broker=settings.redis_url,
    )


router = APIRouter(prefix="/v1", tags=["ingest"])


# ---------------------------------------------------------------------------
# POST /v1/documents/upload
# ---------------------------------------------------------------------------
@router.post("/documents/upload", response_model=UploadResponse)
def upload_document(
    # `File(...)` and `Form(...)` tell FastAPI this is a multipart form.
    # `UploadFile` gives us a file-like object we can read/copy.
    file: UploadFile = File(..., description="The legal document file (PDF, DOCX, TXT, etc.)"),
    title: str = Form(..., description="Title of the legal document"),
    jurisdiction: str = Form(None, description="Jurisdiction (e.g., US, EU, EG)"),
    year: int = Form(None, description="Year of the document"),
    law_type: str = Form(None, description="Type: statute, regulation, case_decision, etc."),
    db: Session = Depends(get_db),
):
    """
    Upload a legal document and start background ingestion.

    Returns the created document and its ingest job (initially queued).
    """

    # 1. Generate a unique filename to avoid collisions.
    #    We keep the original extension so we know the file type later.
    original_ext = Path(file.filename).suffix if file.filename else ""
    stored_name = f"{uuid.uuid4()}{original_ext}"
    dest_path = os.path.join(settings.upload_dir, stored_name)

    # 2. Save the file to disk.
    #    `shutil.copyfileobj` streams the data so we don't load the
    #    entire file into memory (important for large PDFs).
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # 3. Create the Document record in Postgres.
    doc = Document(
        title=title,
        jurisdiction=jurisdiction,
        year=year,
        law_type=law_type,
        file_path=dest_path,
    )
    db.add(doc)
    db.flush()  # flush sends the INSERT to the DB so doc.id is populated.

    # 4. Create the IngestJob record (status starts as "queued").
    job = IngestJob(document_id=doc.id, status="queued")
    db.add(job)
    db.flush()

    # 5. Commit the transaction — both rows are saved atomically.
    db.commit()

    # 6. Send the Celery task to the queue.
    #    `send_task` dispatches by task name without needing the function.
    #    We pass the job_id as a string because UUIDs aren't JSON-serializable.
    celery = _celery_app()
    celery.send_task("worker.tasks.process_document", args=[str(job.id)])

    # Refresh ORM objects so response includes server-generated fields
    # like created_at.
    db.refresh(doc)
    db.refresh(job)

    # 7. Return the response immediately. The worker will process
    #    the file in the background, and the client can poll the
    #    job status endpoint to track progress.
    return UploadResponse(
        document=DocumentOut.model_validate(doc),
        job=IngestJobOut.model_validate(job),
    )


# ---------------------------------------------------------------------------
# GET /v1/jobs/{job_id}
# ---------------------------------------------------------------------------
@router.get("/jobs/{job_id}", response_model=IngestJobOut)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Check the current status of an ingest job.

    Clients poll this endpoint after uploading to know when processing
    is complete (or if it failed).
    """
    job = db.query(IngestJob).filter(IngestJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return IngestJobOut.model_validate(job)


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Stream original uploaded PDF for a document.
    Used by the chat UI evidence viewer.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path:
        raise HTTPException(status_code=404, detail="Document file is missing")

    p = Path(doc.file_path).resolve()
    upload_root = Path(settings.upload_dir).resolve()
    if not p.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")
    if upload_root not in p.parents and p != upload_root:
        raise HTTPException(status_code=403, detail="Invalid file path")
    if p.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF preview is supported")

    safe_name = "".join(ch for ch in (doc.title or "document") if ch.isalnum() or ch in (" ", "_", "-")).strip() or "document"
    return FileResponse(
        path=str(p),
        media_type="application/pdf",
        filename=f"{safe_name}.pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}.pdf"'},
    )
