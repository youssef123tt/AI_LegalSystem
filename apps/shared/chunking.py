"""
Chunking utilities.

Milestone 3: paragraph-aware, character-based chunking with overlap.
Milestone 6 will replace/augment this with section-aware parsing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkPiece:
    ordinal: int
    text: str
    char_start: int | None = None
    char_end: int | None = None


def chunk_text_basic(
    text: str,
    *,
    max_chars: int = 2000,
    overlap_chars: int = 200,
) -> list[ChunkPiece]:
    """
    Split text into chunks.

    Strategy:
    - Split on paragraph breaks (blank line) first.
    - Greedily pack paragraphs into chunks up to max_chars.
    - Add a small overlap between chunks to keep boundary context.
    """
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    pieces: list[str] = []
    for p in paragraphs:
        # If a single paragraph is huge, hard-split it.
        if len(p) <= max_chars:
            pieces.append(p)
            continue
        start = 0
        while start < len(p):
            pieces.append(p[start : start + max_chars])
            start += max_chars

    chunks: list[ChunkPiece] = []
    current = ""
    ordinal = 0

    def _flush():
        nonlocal current, ordinal
        if current.strip():
            chunks.append(ChunkPiece(ordinal=ordinal, text=current.strip()))
            ordinal += 1
        current = ""

    for piece in pieces:
        if not current:
            current = piece
            continue

        # +2 is for the "\n\n" join we use between paragraphs.
        candidate_len = len(current) + 2 + len(piece)
        if candidate_len <= max_chars:
            current = f"{current}\n\n{piece}"
        else:
            _flush()
            current = piece

    _flush()

    if overlap_chars > 0 and len(chunks) > 1:
        overlapped: list[ChunkPiece] = []
        for i, ch in enumerate(chunks):
            if i == 0:
                overlapped.append(ch)
                continue
            prev = overlapped[-1].text
            overlap = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
            merged = (overlap + "\n\n" + ch.text).strip()
            overlapped.append(ChunkPiece(ordinal=ch.ordinal, text=merged))
        chunks = overlapped

    return chunks

