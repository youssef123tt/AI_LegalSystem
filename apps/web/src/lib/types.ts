export type UUID = string;

export type DocumentOut = {
  id: UUID;
  title: string;
  jurisdiction?: string | null;
  year?: number | null;
  law_type?: string | null;
  created_at: string;
};

export type IngestJobOut = {
  id: UUID;
  document_id: UUID;
  status: string;
  needs_ocr?: boolean | null;
  needs_review?: boolean | null;
  extraction_method?: string | null;
  quality_score?: number | null;
  arabic_letter_count?: number | null;
  arabic_presentation_forms?: number | null;
  replacement_char_count?: number | null;
  has_tounicode?: boolean | null;
  indexed?: boolean | null;
  indexed_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type UploadResponse = {
  document: DocumentOut;
  job: IngestJobOut;
};

export type ChunkOut = {
  id: UUID;
  document_id: UUID;
  ordinal: number;
  section_path?: string[] | null;
  text: string;
  created_at: string;
};

export type SearchFilters = {
  jurisdiction?: string | null;
  law_type?: string | null;
  year_min?: number | null;
  year_max?: number | null;
};

export type SearchRequest = {
  query: string;
  filters?: SearchFilters | null;
  top_k?: number;
  mode?: string | null;
  keyword_weight?: number | null;
  vector_weight?: number | null;
};

export type SearchHit = {
  chunk_id: string;
  document_id: string;
  document_title?: string | null;
  section_path: string[];
  ordinal?: number | null;
  page_start?: number | null;
  page_end?: number | null;
  score?: number | null;
  snippet: string;
  jurisdiction?: string | null;
  year?: number | null;
  law_type?: string | null;
  source?: string | null;
  citations?: string[];
  citation_types?: string[];
  citation_official_urls?: string[];
};

export type SearchResponse = {
  index: string;
  hits: SearchHit[];
};

export type SectionOutlineItem = {
  path: string[];
  chunk_count: number;
  first_ordinal: number;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type ChatRequest = {
  messages: ChatMessage[];
  filters?: SearchFilters | null;
  top_k?: number;
  mode?: string | null;
  llm_provider?: "openrouter" | "gemini" | null;
  llm_model?: string | null;
  max_tokens?: number | null;
};

export type ChatResponse = {
  answer: string;
  sources: SearchHit[];
  model_used?: string | null;
  provider_used?: string | null;
};

export type ReportRequest = {
  query: string;
  filters?: SearchFilters | null;
  top_k?: number;
  mode?: string | null;
  llm_provider?: "openrouter" | "gemini" | null;
  llm_model?: string | null;
  max_tokens?: number | null;
};

export type ReportResponse = {
  report: string;
  sources: SearchHit[];
  model_used?: string | null;
  provider_used?: string | null;
};
