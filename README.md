# AI Legal Knowledge Assistant

Milestone 2 adds document upload, database tables, and background job processing.

## Run (dev)

1. Create `.env` from `.env.example`.
2. Start services:

```powershell
.\scripts\dev.ps1
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check |
| `GET` | `/version` | App name + environment |
| `GET` | `/healthz/deps` | Dependency connectivity check |
| `POST` | `/v1/documents/upload` | Upload a legal document |
| `GET` | `/v1/jobs/{job_id}` | Check ingestion job status |

API docs: `http://localhost:8000/docs`

## Web UI (Milestone 3)

The web UI lives in `apps/web` and talks to the API via a Vite dev proxy (so browser requests to `/v1/...` are forwarded to `http://localhost:8000`).

Run:

```powershell
cd D:\AI_LegalSystem\apps\web
npm install
npm run dev
```

Open:

- Web UI: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
