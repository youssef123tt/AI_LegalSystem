# Milestone 5 Plan: Legal Citation Extraction + Linking (Detailed, Testable)

This document explains exactly what we will implement for citation extraction and linking, and what documents you can use to test it.

We will implement this after finishing "stabilize ingestion + indexing".

## 1) Goal (What This Feature Does)

When a document is ingested and chunked, the system will:

1. Detect legal citations inside each chunk (examples: statutes, regulations, cases).
2. Normalize them into a consistent representation (so duplicates can be recognized).
3. Link citations to documents inside our corpus when possible.
4. Store citation relationships so we can build:
   - citation linking
   - citation graph (advanced feature later)
5. Expose citations in API responses for lawyer workflows later.

## 2) What We Will Implement (Concrete Scope)

### 2.1 Extraction (Rule-based v1)

We will implement a first version that is rule-based (regex + heuristics), not LLM-based.

Why rule-based first:
- deterministic
- fast
- easy to audit/debug
- avoids hallucinations

#### Citation types (v1)

US-focused (good initial coverage):

- US statutes:
  - `18 U.S.C. § 1030`
  - `15 USC 78j`
- CFR regulations:
  - `17 C.F.R. § 240.10b-5`
  - `29 CFR 1910.1200`
- US cases (basic):
  - `Roe v. Wade, 410 U.S. 113 (1973)`
  - `Brown v. Board of Education, 347 U.S. 483 (1954)`

Arabic / Egypt-style (basic v1 patterns):

- Egyptian law references:
  - `القانون رقم 14 لسنة 2025`
  - `قانون رقم 14 لسنة 2025`
- Official gazette references (if present):
  - `الجريدة الرسمية`
  - issue/date patterns if clearly present
- Article references (in Arabic and English):
  - `المادة (3)` / `المادة 3`
  - `Article 3`, `Section 4`

EU/UN: we can add later; v1 may only catch obvious patterns if present.

### 2.2 Normalization (Canonical keys)

We will normalize extracted citations into a canonical identifier so the same citation matches even if written differently.

Examples:

- `18 U.S.C. § 1030` and `18 USC 1030` normalize to:
  - `us:usc:18:1030`
- `17 C.F.R. § 240.10b-5` normalizes to:
  - `us:cfr:17:240.10b-5`
- `القانون رقم 14 لسنة 2025` normalizes to:
  - `eg:law:2025:14`

We also store the **raw text** that appeared in the chunk so you can show it in UI.

### 2.3 Storage (New tables)

We will add tables:

- `citations`
  - `id` (uuid)
  - `canonical_id` (unique string)
  - `citation_type` (e.g., `usc`, `cfr`, `case`, `eg_law`)
  - `jurisdiction` (e.g., `US`, `EG`)
  - `display` (preferred display string)
  - `created_at`

- `chunk_citations`
  - `id` (uuid)
  - `chunk_id` (fk chunks.id)
  - `citation_id` (fk citations.id)
  - `raw_text` (the exact match from the chunk)
  - `start_char`, `end_char` (offsets in chunk text, optional)
  - `created_at`

- `citation_edges` (graph foundation)
  - `id` (uuid)
  - `from_document_id` (fk documents.id)
  - `to_citation_id` (fk citations.id) OR `to_document_id` (if linked internally)
  - `created_at`

We will keep the schema flexible; linking can start simple.

### 2.4 Linking (Internal corpus linking)

Linking means:

- If a citation points to a document we have already ingested, store a direct link.

Linking v1 heuristics:

- If `canonical_id` matches a document’s known ID (future)
- Or match by document title patterns for very specific types (limited)

For v1, we will likely store the citation as an external reference, and only do internal linking when we have stable IDs for laws/cases in our corpus.

### 2.5 Indexing into OpenSearch (citation fields)

We will enrich each OpenSearch chunk document with:

- `citations`: array of canonical IDs
- `citation_types`: array of types

This enables:

- filtering by citation presence
- finding chunks mentioning a specific statute

## 3) API Outputs (What You’ll See)

### 3.1 List chunks endpoint

Optionally add a query param:

- `GET /v1/documents/{document_id}/chunks?include_citations=true`

Response includes citations per chunk.

### 3.2 Search endpoint

`POST /v1/search` will include:

- citations array in each hit (optional toggle)

## 4) Testing: What Documents To Use

You can test citation extraction with either:

### 4.1 English / US test documents

Best sources:

- Court opinions (PDF text-based) that include citations:
  - Supreme Court opinions (often cite U.S. reporters)
  - Federal appellate opinions
- Regulations / CFR excerpts with explicit `C.F.R.` citations
- Statutes or legal memos that include `U.S.C.` citations

What to look for:

- Strings like:
  - `U.S.C.`
  - `C.F.R.`
  - `v.` (case "versus")
  - reporter formats like `410 U.S. 113 (1973)`

### 4.2 Arabic / Egypt test documents

Best sources:

- Egyptian laws in PDF (text-based if possible)
  - Documents that include: `القانون رقم ... لسنة ...`
- Official Gazette PDFs where law numbers and years are stated
- Legal commentary PDFs that cite law numbers and articles

What to look for:

- `القانون رقم 14 لسنة 2025`
- `المادة (3)` or `المادة 3`
- `الجريدة الرسمية`

Important note:

- If your Arabic PDF extraction is flagged `needs_ocr`, citation extraction will be unreliable (because it depends on readable text).

## 5) Acceptance Criteria (How We Know It Works)

For at least 3 test documents:

- Extracted citations appear in DB tables.
- Citations are normalized (canonical IDs are stable).
- Search results can return the citations array for each chunk.
- At least one document produces > 10 citations from multiple chunks (typical for court opinions).

## 6) Limitations (v1)

- Citation extraction is pattern-based; it won’t catch everything.
- Internal linking is limited until we have stable corpus identifiers or a curated corpus.
- Arabic extraction quality limits citation detection (OCR later improves).

## 7) Implementation Notes (Engineering)

- Implement extractors as pure functions: `extract_citations(text) -> list[Match]`
- Store match offsets when possible (for UI highlighting later)
- Deduplicate citations per chunk
- Use DB unique constraints on `citations.canonical_id`

