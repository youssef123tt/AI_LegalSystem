# Web UI Stack + What We'll Build (Before Implementation)

This document locks the web stack and describes exactly what we will add to the repo to provide a nice UI for the features we have today (Milestone 3).

## Goal (Web Part)

Provide a browser UI that can:

- Upload a document with metadata (title, jurisdiction, year, law_type)
- Show job status (queued/processing/complete/failed/needs_ocr)
- List chunks for a document
- Run keyword search with filters and show highlighted snippets
- Let you copy IDs and drill into results easily

## Recommended Stack (Production-Friendly, Simple to Maintain)

### Frontend

- Framework: React + Vite
- Language: TypeScript
- Styling: Tailwind CSS
- UI primitives (accessible components): Radix UI
- Forms: React Hook Form + Zod (client-side validation)
- Data fetching + caching: TanStack Query (React Query)
- Icons: Lucide
- Notifications: lightweight toast component (or Radix toast)

Why this stack:

- Vite is fast and straightforward for a dashboard-style app.
- TypeScript helps prevent UI/API mismatch bugs.
- Tailwind + Radix gives a clean, modern, accessible UI without heavy dependencies.
- TanStack Query makes polling job status and caching search results easy and reliable.

### Backend Changes (Small, for Web Support)

- Add CORS middleware in FastAPI (so the web app can call the API in dev).
  - Alternatively, use a Vite dev proxy to avoid CORS. We will do BOTH:
    - Vite proxy for dev convenience
    - CORS enabled for flexibility (optional but recommended)

No authentication is required yet (Public/Lawyer separation comes later). We will keep the UI "single-user local dev" for now.

## What We Will Create in This Repo

### New App Folder

- `apps/web/` (new Vite React app)

Inside it we will add:

- `package.json` + `vite.config.ts` (with dev proxy to `http://localhost:8000`)
- `src/`
  - `main.tsx`, `App.tsx`
  - `lib/api.ts` (typed API client wrappers)
  - `lib/types.ts` (shared TS types that match FastAPI schemas)
  - `components/`
    - layout: sidebar/topbar, page container
    - reusable: button/input/select, badge, toast, loading states
  - `pages/`
    - `UploadPage` (upload + metadata)
    - `JobsPage` / `JobDetailPage` (poll status)
    - `SearchPage` (query + filters + results)
    - `DocumentChunksPage` (list chunks for a document)

### UI Pages (What Each Page Does)

1. Upload
   - File picker (PDF/DOCX/TXT)
   - Fields:
     - title (required)
     - jurisdiction (optional, but recommended; ex: `US`, `EU`)
     - year (optional, but recommended; ex: `2020`)
     - law_type (optional; ex: `contract`, `regulation`, `case_decision`)
   - On success:
     - Show `document_id` and `job_id`
     - One-click buttons: "Open Job", "View Chunks", "Search This Corpus"

2. Job Status
   - Input: `job_id` (or navigated from Upload)
   - Poll `GET /v1/jobs/{job_id}` every 1-2 seconds until terminal state:
     - complete / failed / needs_ocr
   - If `failed`, show `error_message`.
   - If `needs_ocr`, explain: "This PDF is likely scanned. OCR comes in Milestone 4."

3. Search (Keyword-only for now)
   - Query box + filters:
     - jurisdiction
     - law_type
     - year_min, year_max
   - Calls `POST /v1/search`
   - Shows:
     - highlighted snippet (render `<em>` safely)
     - score
     - document_title
     - year/jurisdiction/law_type badges
     - buttons: "Copy chunk_id", "Open document chunks"

4. Document Chunks
   - Input: `document_id`
   - Calls `GET /v1/documents/{document_id}/chunks`
   - Shows chunks ordered by `ordinal`
   - Search within document (client-side find)
   - Copy chunk text / IDs

### Nice UI Details (What “Nice” Means Here)

- Clean layout with a sidebar (Upload / Jobs / Search / Chunks)
- Color-coded status badges:
  - queued (gray), processing (blue), complete (green), failed (red), needs_ocr (amber)
- Loading states and empty states that explain what to do next
- Small “help” text that teaches the workflow (since you’re learning the system)

## API Endpoints We Will Use (Current System)

- Upload: `POST /v1/documents/upload` (multipart/form-data)
- Job status: `GET /v1/jobs/{job_id}`
- Chunks: `GET /v1/documents/{document_id}/chunks?limit=&offset=`
- Search: `POST /v1/search` (JSON)
- OpenSearch init (optional button): `POST /v1/admin/opensearch/init`

## How You Will Run It (Dev)

1. Start backend services (API + worker + DB + OpenSearch).
2. Start web app:
   - `cd D:\\AI_LegalSystem\\apps\\web`
   - `npm install`
   - `npm run dev`
3. Open:
   - Web UI: Vite dev server URL (usually `http://localhost:5173`)
   - API: `http://localhost:8000/docs`

## What We Are NOT Doing Yet (Future Milestones)

- Login / roles (Public vs Lawyer) and rate limiting
- OCR workflow UI (Milestone 4)
- Citation extraction UI (Milestone 5)
- Section-aware navigation (Milestone 6)
- Hybrid search (vectors) and similarity search (Milestone 7+)

## Implementation Order (Web)

1. Scaffold `apps/web` with routing + layout
2. Add API client + TS types
3. Build Upload page (end-to-end)
4. Build Job status polling UI
5. Build Chunks page
6. Build Search page + result UI
7. Add “OpenSearch init” admin button (optional)

