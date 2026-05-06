"""
FastAPI application entry point.

WHAT CHANGED IN MILESTONE 2
----------------------------
- Added the `ingest` router (upload + job-status endpoints).
- Added a `lifespan` event that creates the upload directory on startup.
- Existing health endpoints are unchanged.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opensearchpy import OpenSearch

from app.settings import settings
from app.routers import ingest
from app.routers import admin_opensearch
from app.routers import search
from app.routers import admin_reprocess
from app.routers import chat
from app.routers import reports
from app.routers import audit
from app.opensearch_utils import ensure_chunks_index

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: code that runs once at startup / shutdown.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs when the server starts up, before any requests are handled.
    We use it to make sure the upload directory exists.

    The `yield` separates startup logic (above) from shutdown logic (below).
    """
    os.makedirs(settings.upload_dir, exist_ok=True)
    if settings.opensearch_init_on_startup:
        try:
            status = ensure_chunks_index()
            logger.info("OpenSearch init: %s", status)
        except Exception as exc:
            # Don't block API startup; /healthz/deps will show OpenSearch issues.
            logger.warning("OpenSearch init failed: %s", exc)
    yield
    # (Shutdown logic would go here if we needed any.)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Register the ingest router (adds /v1/documents/upload and /v1/jobs/{job_id}).
app.include_router(ingest.router)
app.include_router(admin_opensearch.router)
app.include_router(search.router)
app.include_router(admin_reprocess.router)
app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(audit.router)


# ---------------------------------------------------------------------------
# Health / version endpoints (unchanged from Milestone 1)
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"name": settings.app_name, "env": settings.app_env}


@app.get("/healthz/deps")
def healthz_deps():
    """
    Lightweight dependency check for Milestone 1.
    """
    client = OpenSearch(hosts=[settings.opensearch_url])
    info = client.info()
    return {
        "status": "ok",
        "opensearch": {"cluster_name": info.get("cluster_name"), "version": info.get("version", {}).get("number")},
    }
