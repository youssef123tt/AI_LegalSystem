"""
Section-aware chunking (Milestone 6).
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.chunking import chunk_text_basic
from shared.sections import parse_section_spans


@dataclass(frozen=True)
class SectionChunk:
    ordinal: int
    text: str
    section_path: list[str]


def chunk_text_section_aware(
    text: str,
    *,
    max_chars: int = 2000,
    overlap_chars: int = 200,
) -> list[SectionChunk]:
    """
    Chunk text but preserve document structure.

    - Split document into spans using headings (Article/Section/etc.).
    - Chunk each span separately using the basic chunker.
    - Each chunk gets a `section_path` for navigation and later citations.
    """
    spans = parse_section_spans(text)
    if not spans:
        return []

    out: list[SectionChunk] = []
    ordinal = 0
    for sp in spans:
        span_text = text[sp.start_char : sp.end_char].strip()
        if not span_text:
            continue
        pieces = chunk_text_basic(span_text, max_chars=max_chars, overlap_chars=overlap_chars)
        for p in pieces:
            out.append(SectionChunk(ordinal=ordinal, text=p.text, section_path=sp.section_path))
            ordinal += 1
    return out

