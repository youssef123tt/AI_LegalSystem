# System Architecture (Detailed)

This document explains the target architecture for the "AI Legal Knowledge Assistant" (Enterprise Legal Document RAG System). It is written for someone new to RAG systems and new to modern backend architectures.

It covers:

- Each part of the architecture and why it exists
- The end-to-end workflows (ingestion, search, chat, reporting)
- Practical use cases and examples

## 1) What We're Building (One Sentence)

A system that ingests legal documents (PDF/DOCX/scans), extracts structured text and citations, indexes content for hybrid search (keyword + vectors), and exposes two chat experiences (public + lawyer) that answer questions with traceable sources.

## 2) High-Level Components

The system is split into "online request" services and "offline heavy processing" services.

### Architecture Diagram (Bird's-Eye View)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNplkMFugzAMhu99CisnqqnqfYdJ3aRtlajGYFUPqIcABrJSjJxkiD39TNAO3S5x7P_7Y8d1R2PZanYQpysAb5FzdZTTQvRknPnGHrYQ63FCXqszbDYP4E2uTlhI_UCF6RCOe3WezSbIehB9l-whetbWyUV8K5GlHvShyVVC1jWM0iQjzyUC1fDB3rXr8NIvSjZXbwP2GWouW4hep4JNBUt6i3bdNVdxfICE6ctUyBDNzpS8Q76HF7ya3vyZhLEy0iGdA0TvHj1uH5ku4avCBT2QI_Fl3swpRFkNdsjTQi1awKwjRhm5-MTSQSaZbhCiVI9wBzt2ptals_9sQ3Obk_0Bpu991g==)

`mermaid
flowchart LR
  user["Users (Citizen / Lawyer)"] --> ui["Web / Mobile UI"]
  ui --> api["API (FastAPI)"]

  api --> pg["Postgres (Source of Truth)"]
  api --> os["OpenSearch (Hybrid Search)"]
  api --> llm["LLM Provider (OpenRouter: Gemini)"]

  api --> redis["Redis (Queue/Broker)"]
  redis --> worker["Worker (Celery)"]
  worker --> store["Object Storage (Raw + Artifacts)"]
  worker --> pg
  worker --> os
```

### 2.1 API Service (FastAPI)

Responsibilities:

- Accept uploads and metadata (jurisdiction, year, law type)
- Provide search endpoints (hybrid retrieval + filters)
- Provide bot endpoints (Public bot and Lawyer bot)
- Provide report generation endpoints (lawyer-only)
- Provide health endpoints for operations

Why it exists:

- Web/mobile clients need a stable HTTP API
- We must keep user requests fast; heavy processing should not run inside request/response

### 2.2 Worker Service (Celery)

Responsibilities:

- Run long, heavy tasks asynchronously:
  - OCR on scanned PDFs
  - PDF/DOCX text extraction
  - section parsing and chunking
  - citation extraction and normalization
  - embeddings generation
  - indexing to OpenSearch

Why it exists:

- OCR and embedding can take seconds or minutes
- Background jobs allow retries, monitoring, and scaling separate from the API

### 2.3 Redis (Queue/Broker)

Responsibilities:

- Messaging system between API and Worker
- Holds tasks to be processed (job queue)
- Stores task status/results (basic usage)

Why it exists:

- It's the "mailbox" where the API drops work and workers pick it up

### 2.4 Postgres (Relational Database, Source of Truth)

Responsibilities:

- Store the authoritative metadata and structured outputs:
  - documents and versions
  - ingestion jobs and statuses
  - chunks metadata (IDs, section paths, offsets)
  - extracted citations and normalized forms
  - citation graph edges
  - timeline/version metadata (effective dates, amendments)
  - access control objects (users, roles) later

Why it exists:

- We need strong consistency for business records (document metadata, job state)
- We need flexible queries and joins (filters, graph edges, time-based queries)

What it is not used for (by default):

- We will not use Postgres as the main hybrid search engine if we commit to OpenSearch at production scale

### 2.5 OpenSearch (Hybrid Search Engine)

Responsibilities:

- Store searchable chunk documents in an index
- Support:
  - keyword search (BM25)
  - vector search (kNN)
  - hybrid queries that combine both
  - filters (jurisdiction/year/law_type)

Why it exists:

- Search systems are specialized; OpenSearch is built for ranking, scoring, and filtering at scale
- Hybrid search is a core requirement

### 2.6 Object Storage (Raw Files + Derived Artifacts)

What we store:

- Raw uploads: PDF, DOCX
- Derived assets: OCR page images (optional), extracted text files (optional)

In development:

- Start with local filesystem paths

In production:

- Move to S3-compatible storage (AWS S3, MinIO, etc.)

Why it exists:

- Databases are not ideal for large binary files
- Keeping original documents is important for auditability

### 2.7 LLM Provider (OpenRouter using Gemini)

Responsibilities:

- Generate answers for bots and structured lawyer reports
- Optionally help with:
  - summarizing long laws
  - extracting structured fields (carefully, with validation)
  - re-ranking search results (optional)

Why it exists:

- Users want "natural language answers"
- Lawyers want synthesized reports with citations

Important rule:

- LLM output must be grounded in retrieved sources, and we must return those sources

## 3) Data Model (Conceptual)

These are the main conceptual entities (tables and indexes will reflect this).

- Document: a legal item (law, regulation, decision)
- DocumentVersion: version of a document over time (supports timeline)
- Chunk: a piece of text used for retrieval (section-aware: article/clause)
- Citation: normalized citation reference (e.g., a statute or a case)
- ChunkCitation: links a chunk to citations mentioned inside it
- CitationEdge: citation graph relationship (A cites B)
- IngestJob: background job tracking (upload -> processed -> indexed)

## 4) Core Workflows (End-to-End)

### 4.1 Workflow A: Document Ingestion (Upload -> Searchable)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNplUstu3DAMvOcreHQQFL37ECCwu0EKFDZ2W7i3gpZYr7K25FB0u-3Xl_IjCdyTKc1wOBw50stE3lDpsGMcbgBwkuCnoSXWw4gszrgRvUABGKHoHXnZIQ_1U8LSJztgFC1ud5TT1ypRqvaZjJ4kMHa049SPiVKHKB1T3IHHhB3Juj3QJKAJfCGGrKCe-M9-eHWaZ4_kT4RszjeKFx_u79VnDt_GPqCFn64nuIOBBC0KKkNR5ajxfPZLwPh7oWV1efhYVsX321da_ZhDwYRCUAYzDRqSqj35jqJ8Di1kGvNE9q3hmMMnP1-Cm1nwHNoVVbjIdVmZ2INd5X44q4pK0iIt0CwiJS0iS3ezOT6QmPOr4xVpdOZVGPUFhK7ybg8IDFVxhCwa9H7xuXbUyJEg6rO54KNaMOfJX2aB_2XvwAcesHd_CYwTnHveaGtCpH-Xtbp2hOyXCgeO28CU45L2PGaet-loTbajTa865RqwpauaS6-Kbb91vRP7gnxJ4YAJw9iT0D9ohvB9)

`mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as API (FastAPI)
  participant STO as Object Storage
  participant PG as Postgres
  participant R as Redis
  participant W as Worker (Celery)
  participant OS as OpenSearch

  C->>API: Upload file + metadata
  API->>STO: Store raw file (PDF/DOCX)
  API->>PG: Create Document + IngestJob (queued)
  API->>R: Enqueue ingest job
  API-->>C: Return document_id + job_id

  W->>R: Dequeue job
  W->>STO: Fetch raw file
  W->>W: Extract text (PDF/DOCX) or OCR (scanned)
  W->>W: Parse sections + chunk text
  W->>W: Extract + normalize citations
  W->>W: Create embeddings (vectors)
  W->>PG: Store chunks + citations + edges
  W->>OS: Index searchable chunks
  W->>PG: Mark job complete
```

Goal:

Take a raw PDF/DOCX/scanned PDF and turn it into:

- extracted text
- section-aware chunks
- extracted citations
- embeddings
- OpenSearch index documents

Step-by-step:

1. Client uploads a file and metadata to API.
2. API stores raw file in object storage and writes a Document record in Postgres.
3. API enqueues an ingest job to Redis and returns a Job ID.
4. Worker picks up the job.
5. Worker extracts text:
   - If PDF has text: parse it.
   - If PDF is scanned: OCR.
   - If DOCX: extract text via DOCX parser.
6. Worker runs section parsing:
   - Identify "Article", "Section", "Clause" headings.
   - Build a section path like `Article 3 -> Clause 2`.
7. Worker chunks text:
   - Each chunk has a stable ID and metadata (doc_id, section_path, offsets).
8. Worker extracts legal citations from each chunk:
   - Stores both raw citation strings and normalized forms.
9. Worker generates embeddings for each chunk (vector representation).
10. Worker writes chunk documents to OpenSearch:
   - Fields: text, doc_id, section_path, jurisdiction, year, law_type, citations, embedding vector.
11. Worker updates job status to "complete".
12. Users can now search and chat over this document.

Operational notes:

- If anything fails, the job can be retried.
- We keep raw uploads for auditing and later improvements.

### 4.2 Workflow B: Search (Hybrid + Filters)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNpdkMFOwzAMhu97Ch87wS5IXHqYBAUE0rYiygt4qceipUmIXaS9PU7XDtRLnPj_bP8O03dP3tCTxa-E3QIAewm-7_aU9BExiTU2oheoABkqZ8nLTHl4f8taDsULsuhlOUPqJhN1JN8QJnOcyZvNNus5FCGKDR7dcqFQtVqvtV0Jl7JC3abzLRysE0qcp6g6Mc_quoUBgeIQEvyQEQ081P7BdVPC63mf7BV-3N7dww2cdjs9_zWvm9XU_DNEMMfen1gRNiER599yuttoGBKtEvqTpqdJulAJH5c0sLcxkjAUEoIDNRZT6KIshwJFr7PGCl3GWc6_Tb4d3StSZYB7J9lJR4ItCurVWMHshH8B95mTgw==)

`mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as API (FastAPI)
  participant OS as OpenSearch
  participant LLM as LLM (optional)

  C->>API: Search(query, filters)
  API->>API: Embed query (for vector search)
  API->>OS: Hybrid query (BM25 + kNN + filters)
  OS-->>API: Top chunks + scores
  alt Optional re-rank
    API->>LLM: Re-rank snippets (tool or prompt)
    LLM-->>API: Re-ranked list
  end
  API-->>C: Results + metadata + citations
```

Goal:

Given a user query and optional filters, return the best chunks and documents.

Example filters:

- jurisdiction = US
- year >= 2019
- law_type = "regulation"

Step-by-step:

1. Client sends a search request to API with query + filters.
2. API calls OpenSearch with a hybrid query:
   - keyword BM25 query on text
   - kNN vector query using query embedding
   - combine scores with weights
3. OpenSearch returns top chunks with scores.
4. API returns chunks + document metadata (and optionally citations).

Why hybrid helps:

- Keyword search is great for exact terms (statute numbers, names).
- Vector search is great for semantic similarity (paraphrased concepts).
- Combining them improves legal search reliability.

### 4.3 Workflow C: Public Bot (Citizen Q&A)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNpdjtFuwjAMRd_5Cj-CED_QB6SKaWgSqBNVP8BLLbCgTuc4IPH1c8ZAU5-S-B6f3ETfmSTQG-NRcZgBYLYoefgi9ceIahx4RDHoABNs2PhOMonqz48SlmP-jsn8spggTVuIZiRpCTWcJvFut3_mh5iNFOZbGlh4MXOyW63X7qygTmfwwsk4lg4-86RpKziQKdOVQOlC12IMpyzn5FDTrp7rm98ZLGEgwx4NXw7_v4ItCSkaAUq6eYWjxiw99cACKWYNVHyOvoT1A1xCYMNSKv0ZHej-xY9tuHCyH1ljd-c=)

`mermaid
sequenceDiagram
  autonumber
  participant U as Citizen
  participant API as API (FastAPI)
  participant OS as OpenSearch
  participant LLM as OpenRouter (Gemini)

  U->>API: Ask question
  API->>OS: Retrieve relevant chunks
  OS-->>API: Chunks + metadata
  API->>LLM: Generate answer grounded in sources
  LLM-->>API: Answer + citations
  API-->>U: Answer + source list
```

Goal:

Answer general legal questions, without advanced tooling, and with safe boundaries.

Step-by-step:

1. User asks a question in plain language.
2. API runs search with broad defaults.
3. API feeds top sources (chunks) into the LLM as context.
4. LLM generates a grounded answer.
5. API returns:
   - answer
   - list of sources used (document + section + excerpt)

Safety defaults:

- Clear disclaimer: informational, not legal advice
- Encourage consulting a lawyer for personal/complex matters
- Avoid guessing; if sources are insufficient, say so

### 4.4 Workflow D: Lawyer Bot (Advanced)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNplkMFugzAMhu99Ch-pqqp3DpWqVWOTmEDjCdzglghIWOK069vPVgWbuhNB_-cvvxPpK5EzdLR4CTiuADCxd2k8UZCfCQNbYyd0DCVghBJv93_JoX7XTD_ZK0aWw_oJqRolqolcQxhM9xTXhca1j3wJFJ8vLj_m4U-fmAJkBY3W2fVKyHK738uFORxiDxm2V5R1WjjbQcgIG7COybEWEkzgqsnh7X4KtoVAHCxdcYCb5W6eEbJqtrP2pUuuV080_tHtoamLXCqx9U7GjWXUI8gjTh3sYCTGFhlh8L5Pk47VxeIslNopIxViGvhXK8vmcAx4ZnH55FrSmnHyLhJkkUMynAK1uo-wi_Lg4k1eZrNUmZXq_BNHn4Ih3Ye-OaBh8S8jP3ZerDE=)

`mermaid
sequenceDiagram
  autonumber
  participant L as Lawyer
  participant API as API (FastAPI)
  participant OS as OpenSearch
  participant PG as Postgres
  participant LLM as OpenRouter (Gemini)

  L->>API: Ask (advanced filters + intent)
  API->>OS: Hybrid retrieval with filters
  OS-->>API: Chunks + scores
  API->>PG: Optional citation graph / metadata lookups
  PG-->>API: Graph/meta results
  API->>LLM: Draft grounded response (structured)
  LLM-->>API: Answer + citations
  API-->>L: Answer + sources + extracted citations
```

Goal:

Support advanced search and lawyer workflows:

- deeper filters
- precedent retrieval
- better citation-focused outputs

Step-by-step:

1. Lawyer selects jurisdiction + law type + date range.
2. API runs hybrid search with tighter filtering and more results.
3. Optional: re-rank results focusing on legal citations, procedural posture, and authority hierarchy (later).
4. LLM generates:
   - structured summary
   - key holdings
   - cited statutes/cases
   - recommendations for further research
5. API returns answer + sources + extracted citations.

### 4.5 Workflow E: Legal Report Generation (Lawyer)

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNo9kE1OxDAMhfecwsoKBHMBFiwQyyKhEWITdWGlZhqRNsU_M5rb42ZaNsmT_b3nxN-lXtKIrPD5dgfA9BtDh5crseulet1LRqKhh8PhBZaCcwwffoIQchpJ4F4U1ZTkCRLKejGdrKDmOstD6D13tTU_k3KmM8VwtBkmK5qXQv9ZDd6Z20BMPzG8Wi4DJGNUGkCqcaLWuqW7aPCJ_HFd974KWlkBUbakxm6baKqN927Dz1jy4FQMX5t6Bp_LV0gF8wQjCuA2rRl3Q3NXU_8Fefa87-pxg8VVyto2ABMuof8DzTZ6ng==)

`mermaid
flowchart TD
  req["Lawyer report request"] --> plan["Plan searches (statutes, cases, regulations)"]
  plan --> retrieve["Run multiple searches"]
  retrieve --> pack["Build curated source pack"]
  pack --> gen["LLM generates structured memo"]
  gen --> validate["Validate: every claim has a source"]
  validate --> out["Return report + sources + citation map"]
```

Goal:

Generate a structured report (like a memo) with citations.

Typical sections:

- Issue
- Facts (if user provides)
- Applicable Law
- Analysis
- Precedents
- Conclusion

Process:

1. Lawyer requests a report with a topic and constraints.
2. API performs multiple targeted searches:
   - broad law overview
   - statute retrieval
   - precedent cases search
3. API builds a "source pack" (curated chunks).
4. LLM generates the report strictly grounded in source pack.
5. API returns markdown and a citation list (source mapping).

Why this is separate from normal chat:

- It is longer, structured, and requires deliberate retrieval.

## 5) Advanced Features (How They Fit)

### 5.1 Legal Citation Graph

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNpLy8kvT85ILCpR8AniUlBwjFZyyU8uzU3NK1FwVNBIzijNyy7WVIpV0NW1q0nOLEktrlFwQlLjpKCv4JxZkliSmZ-n4KQUCzICWa0zklpnZLXOYLUuSNIuqLY4AgDFjjA3)

`mermaid
flowchart LR
  A["Document A (chunks)"] -->|cites| B["Document B / Citation B"]
  A -->|cites| C["Document C / Citation C"]
  D["Document D"] -->|cites| A
```

What it is:

- A graph where nodes are documents/citations and edges represent "A cites B".

Why it matters:

- Helps find authoritative sources
- Helps trace how regulations and cases influence each other

How we build it:

- Each chunk's extracted citations produce edges.
- Store edges in Postgres.
- Provide endpoints to explore inbound/outbound citations.

### 5.2 Timeline of Law Changes

What it is:

- A view of how a law changes over time: amendments, effective dates, superseded versions.

How we support it:

- Store DocumentVersion records with:
  - effective_from / effective_to
  - "amends" relationships
- Add endpoints that return a timeline for a law.

``![Architecture Diagram](https://kroki.io/mermaid/svg/eNpLy8kvT85ILCpR8AniUlAoM4xW8kksB9IKGqlpaanJJZllqQpGBoYGugaGQKSpFKugq2unUGYEVWeEps5U18AMog5kmhFEsTFUsTGqYiOEoQAkkSST)

`mermaid
flowchart LR
  v1["Law v1 (effective 2010-01-01)"] --> v2["Law v2 (effective 2015-06-01)"]
  v2 --> v3["Law v3 (effective 2020-01-01)"]
```

### 5.3 Case Similarity Search

What it is:

- Given a case decision, find similar cases.

How we support it:

- Compute case-level embeddings:
  - either average of chunk embeddings
  - or a dedicated "case summary embedding"
- Query OpenSearch for nearest neighbors.
- Include overlap signals:
  - shared citations
  - shared legal topics (optional taxonomy later)

## 6) Concrete Use Cases (Examples)

### Use Case 1: Citizen asks about workplace discrimination (Public Bot)

User question:

"What laws protect me from discrimination at work?"

System behavior:

- Search for relevant statutes/regulations and authoritative guidance in the selected jurisdiction (or ask user to pick).
- Return an answer that:
  - explains the main protections
  - lists what to search next
  - cites sources (sections/articles)

Expected output style:

- Plain language
- Clear sources
- Not a personalized legal opinion

### Use Case 2: Lawyer wants precedent cases (Lawyer Bot)

User request:

"Find precedent cases about breach of contract where damages were limited by a clause, in US federal decisions after 2015."

System behavior:

- Filter: jurisdiction=US, year>=2015, law_type=case_decision
- Search query includes key terms and semantic similarity
- Return:
  - top cases
  - short holding summaries
  - key cited authorities
  - links to extracted citations

### Use Case 3: Lawyer memo report (Report Generation)

User request:

"Write a memo about whether non-compete clauses are enforceable in jurisdiction X, with citations."

System behavior:

- Retrieve the relevant statutes and cases.
- Generate a memo with:
  - summary of legal standard
  - leading cases and rationale
  - citations that map to specific retrieved sections

### Use Case 4: Trace influence via citation graph

User action:

"Show me what this regulation cites and what cites it."

System behavior:

- Return inbound/outbound edges:
  - `this -> cited_authority`
  - `citing_document -> this`
- Rank by frequency and authority level (future improvement).

### Use Case 5: Compare two court decisions

User action:

"Find similar cases to this decision and explain why they are similar."

System behavior:

- Similarity search on case embeddings
- Explain similarity using:
  - overlapping citations
  - shared legal concepts
  - similar factual patterns (if available)

## 7) Example API Interactions (Illustrative)

These are conceptual examples. Exact endpoints are implemented milestone-by-milestone.

### Example: Upload document (Milestone 2+)

Request idea:

- Upload: PDF file + JSON metadata `{jurisdiction, year, law_type, source}`

Response idea:

- `document_id`
- `job_id`

### Example: Search (Milestone 7)

Request body idea:

```json
{
  "query": "limitations of liability clause enforceability",
  "filters": { "jurisdiction": "US", "year_min": 2015, "law_type": "case_decision" },
  "top_k": 10
}
```

Response idea:

- list of results:
  - doc title
  - section path
  - snippet
  - score
  - citations found in snippet

### Example: Lawyer report (Milestone 8)

Request body idea:

```json
{
  "topic": "Non-compete enforceability in California",
  "jurisdiction": "US-CA",
  "format": "memo"
}
```

Response idea:

- `report_markdown`
- `sources[]`
- `citations[]`

## 8) Production Considerations (What Makes This "Enterprise")

Even if we implement features incrementally, the architecture supports production patterns:

- Clear separation of responsibilities (API vs worker)
- Job queue for heavy tasks
- Consistent source-of-truth database
- Search engine optimized for retrieval
- Observability: health checks, structured logs, metrics (later)
- Security: auth roles for lawyer endpoints, rate limits for public endpoints (later)

## 9) How Milestones Map to Architecture

- Milestone 1: bring up services + health checks
- Milestone 2: Document + Job tables + upload + queue
- Milestone 3: extraction + basic chunking
- Milestone 4: OCR pipeline
- Milestone 5: citations extraction + linking + graph edges
- Milestone 6: section-aware chunking + versioning
- Milestone 7: embeddings + hybrid retrieval + filters
- Milestone 8: two bots + reports
- Milestone 9: citation graph UI endpoints + timeline + case similarity
