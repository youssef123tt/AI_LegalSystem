"""
Milestone 7 (Part 2) Reports Endpoints.
"""

import re

from fastapi import APIRouter, HTTPException

from app.routers.search import search as run_search
from app.schemas import ReportRequest, ReportResponse, SearchHit, SearchRequest
from app.services.llm import LLMError, generate_chat_completion_with_meta

router = APIRouter(prefix="/v1/reports", tags=["reports"])

REPORT_SYSTEM_PROMPT = """You are an expert AI legal assistant for professional lawyers.
Generate a structured legal memorandum using ONLY provided sources.

Rules:
1) No hallucinations. Use only provided source chunks.
2) Cite every factual paragraph with [Chunk ID: <uuid>].
3) If sources conflict, present both views and explain uncertainty.
4) If sources are insufficient, say exactly: not enough sources
5) Distinguish legal rule, evidence, and practical implication.

Output structure:
- Executive Summary
- Detailed Analysis
- Risks / Caveats
- Practical Next Steps

--- SOURCES ---
{sources}
"""

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_CHUNK_INLINE_CIT_RE = re.compile(r"\s*\[Chunk ID:\s*[0-9a-fA-F-]+\]")


def _contains_arabic(text: str) -> bool:
    return bool(_ARABIC_RE.search(text or ""))


def _detect_answer_language(req: ReportRequest, hits: list[SearchHit]) -> str:
    if _contains_arabic(req.query):
        return "ar"
    for h in hits:
        if _contains_arabic(h.snippet or ""):
            return "ar"
    return "en"


def _language_instruction(lang: str) -> str:
    if lang == "ar":
        return (
            "Language policy: Generate the report in Arabic. If some legal terms are better known in English, "
            "you may include the English term in parentheses after the Arabic term."
        )
    return "Language policy: Generate the report in English."


def _strip_inline_chunk_citations(text: str) -> str:
    cleaned = _CHUNK_INLINE_CIT_RE.sub("", text or "")
    lines = [re.sub(r"\s{2,}", " ", ln).strip() for ln in cleaned.splitlines()]
    return "\n".join(lines).strip()


def _sources_footer(hits: list[SearchHit], lang: str, *, limit: int = 12) -> str:
    if not hits:
        return ""
    heading = "## \u0627\u0644\u0645\u0635\u0627\u062f\u0631" if lang == "ar" else "## Sources"
    path_label = "\u0645\u0633\u0627\u0631 \u0627\u0644\u0645\u0635\u062f\u0631" if lang == "ar" else "Source path"
    lines: list[str] = [heading]
    for h in hits[:limit]:
        title = h.document_title or "Unknown Document"
        path = " > ".join(h.section_path) if h.section_path else "N/A"
        pages = f"{h.page_start}-{h.page_end}" if h.page_start else "N/A"
        lines.append(
            f"- [Chunk ID: {h.chunk_id}](chunk://{h.chunk_id}) {title} | {path_label}: {path} | Pages: {pages}"
        )
    return "\n" + "\n".join(lines)


def _format_report_for_readability(report: str, hits: list[SearchHit], lang: str) -> str:
    body = _strip_inline_chunk_citations(report)
    return f"{body}\n\n{_sources_footer(hits, lang)}".strip()


def _build_report_rag_context(req: ReportRequest) -> tuple[str, list[SearchHit]]:
    if not req.query:
        return "", []

    search_req = SearchRequest(
        query=req.query,
        filters=req.filters,
        top_k=req.top_k,
        mode=req.mode or "hybrid",
    )
    search_resp = run_search(search_req)
    hits = search_resp.hits

    if not hits:
        return "", []

    source_texts = []
    for hit in hits:
        jurisdiction = hit.jurisdiction or "Unknown"
        title = hit.document_title or "Unknown Document"
        year = str(hit.year) if hit.year else "N/A"
        section = " > ".join(hit.section_path) if hit.section_path else "N/A"
        pages = f"{hit.page_start}-{hit.page_end}" if hit.page_start else "N/A"
        source_texts.append(
            f"[Chunk ID: {hit.chunk_id}]\n"
            f"Document: {title}\n"
            f"Jurisdiction: {jurisdiction} | Year: {year} | Section: {section} | Pages: {pages}\n"
            f"Snippet: {hit.snippet}\n"
        )

    return "\n\n".join(source_texts), hits


@router.post("/legal", response_model=ReportResponse)
def generate_legal_report(req: ReportRequest):
    sources_text, hits = _build_report_rag_context(req)
    lang = _detect_answer_language(req, hits)

    if not hits:
        return ReportResponse(
            report="\u0645\u0635\u0627\u062f\u0631 \u063a\u064a\u0631 \u0643\u0627\u0641\u064a\u0629" if lang == "ar" else "not enough sources",
            sources=[],
        )

    system_prompt = REPORT_SYSTEM_PROMPT.format(sources=sources_text) + "\n\n" + _language_instruction(lang)
    messages = [{"role": "user", "content": req.query}]

    try:
        report, model_used, provider_used = generate_chat_completion_with_meta(
            messages=messages,
            system_prompt=system_prompt,
            provider=req.llm_provider,
            model=req.llm_model,
            temperature=0.2,
            max_tokens=req.max_tokens,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    report = _format_report_for_readability(report, hits, lang)
    return ReportResponse(report=report, sources=hits, model_used=model_used, provider_used=provider_used)
