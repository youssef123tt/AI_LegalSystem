import type {
  ChunkOut,
  IngestJobOut,
  SearchRequest,
  SearchResponse,
  SectionOutlineItem,
  UploadResponse,
  UUID,
  ChatRequest,
  ChatResponse,
  ReportRequest,
  ReportResponse
} from "./types";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export async function initOpenSearch(): Promise<{ chunks: { index: string; status: string } }> {
  return http("/v1/admin/opensearch/init", { method: "POST" });
}

export async function uploadDocument(input: {
  file: File;
  title: string;
  jurisdiction?: string;
  year?: number;
  law_type?: string;
}): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("title", input.title);
  if (input.jurisdiction) form.append("jurisdiction", input.jurisdiction);
  if (typeof input.year === "number") form.append("year", String(input.year));
  if (input.law_type) form.append("law_type", input.law_type);

  return http("/v1/documents/upload", { method: "POST", body: form });
}

export async function getJob(jobId: UUID): Promise<IngestJobOut> {
  return http(`/v1/jobs/${jobId}`);
}

export async function listChunks(documentId: UUID, limit = 50, offset = 0): Promise<ChunkOut[]> {
  return http(`/v1/documents/${documentId}/chunks?limit=${limit}&offset=${offset}`);
}

export async function getOutline(documentId: UUID): Promise<SectionOutlineItem[]> {
  return http(`/v1/documents/${documentId}/outline`);
}

export async function search(req: SearchRequest): Promise<SearchResponse> {
  return http("/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: req.query,
      filters: req.filters ?? null,
      top_k: req.top_k ?? 10,
      mode: req.mode ?? null,
      keyword_weight: req.keyword_weight ?? null,
      vector_weight: req.vector_weight ?? null
    })
  });
}

export async function chatPublic(req: ChatRequest): Promise<ChatResponse> {
  return http("/v1/chat/public", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
}

export async function chatLawyer(req: ChatRequest): Promise<ChatResponse> {
  return http("/v1/chat/lawyer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
}

export async function generateReport(req: ReportRequest): Promise<ReportResponse> {
  return http("/v1/reports/legal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
}
