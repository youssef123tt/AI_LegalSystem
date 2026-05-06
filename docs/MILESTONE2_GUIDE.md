# Milestone 2 Guide (Beginner-Friendly)

Milestone 2 adds the first real **data path** through the system: a user can upload a legal document, the system saves it, records it in the database, and a background worker acknowledges the job.

## What You Have After Milestone 2

- **Two new database tables** (`documents`, `ingest_jobs`) managed by Alembic migrations.
- **Upload endpoint** (`POST /v1/documents/upload`) that accepts files + metadata.
- **Job status endpoint** (`GET /v1/jobs/{job_id}`) to track background processing.
- **Worker task** (`process_document`) that picks up jobs from the queue and updates their status.
- **Shared package** (`apps/shared/`) containing database models used by both API and Worker.

## New Files Explained

### `apps/shared/` — Shared Code

This package is imported by BOTH the API and Worker containers.

| File | Purpose |
|------|---------|
| `__init__.py` | Makes `shared` a Python package. |
| `database.py` | Creates the SQLAlchemy engine + session factory, plus a FastAPI `get_db()` dependency. |
| `models.py` | Defines `Document` and `IngestJob` ORM classes (mapped to Postgres tables). |
| `alembic.ini` | Alembic configuration (points to the migrations folder). |
| `alembic/env.py` | Tells Alembic where the models are and how to connect to the DB. |
| `alembic/versions/0001_*.py` | First migration: creates the two tables. |

### `apps/api/app/schemas.py` — Pydantic Schemas

Defines the JSON shapes the API returns:
- `DocumentOut` — document metadata (no internal fields like `file_path`).
- `IngestJobOut` — job status details.
- `UploadResponse` — combined response from the upload endpoint.

### `apps/api/app/routers/ingest.py` — Upload & Job Endpoints

Two endpoints:
- `POST /v1/documents/upload`: saves file to disk → creates DB records → sends Celery task.
- `GET /v1/jobs/{job_id}`: looks up job status from DB.

### `apps/worker/worker/tasks.py` — Celery Task

Defines `process_document(job_id)`:
1. Set status → `processing`
2. (Placeholder — actual extraction comes in Milestone 3)
3. Set status → `complete` (or `failed` on error)

## How the Docker Setup Changed

### Build Context
In Milestone 1, each Dockerfile built from its own folder (`apps/api/`).
Now the build context is `apps/` so that Docker can COPY the `shared/` package into both images.

### Migrate Service
A new one-shot service runs `alembic upgrade head` at startup. This creates database tables before the API starts. The API `depends_on` it via `service_completed_successfully`.

### Shared Volume
A `upload_data` volume is mounted at `/data/uploads` in both the API and Worker containers. This lets the Worker (later) read files that the API saved.

## Testing Milestone 2

### 1. Start the stack

```powershell
.\scripts\dev.ps1
```

### 2. Upload a test document

```powershell
curl -X POST http://localhost:8000/v1/documents/upload `
  -F "file=@README.md" `
  -F "title=Test Law" `
  -F "jurisdiction=US" `
  -F "year=2024" `
  -F "law_type=statute"
```

### 3. Check job status

Use the `job.id` from the upload response:

```powershell
curl http://localhost:8000/v1/jobs/<job_id>
```

After a moment, `status` should show `"complete"`.

### 4. Interactive docs

Open `http://localhost:8000/docs` — FastAPI auto-generates a Swagger UI where you can test endpoints in your browser.

## What's Next (Milestone 3 Preview)

Milestone 3 will add real document processing:
- PDF text extraction
- DOCX text extraction
- Basic text chunking

The `process_document` task placeholder will be replaced with actual logic.
