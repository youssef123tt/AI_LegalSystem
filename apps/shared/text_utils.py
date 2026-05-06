"""
Shared text helpers used by both API and worker.
"""

from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")

# Arabic diacritics (tashkeel) often reduce search recall if kept.
_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
# Tatweel / kashida.
_AR_TATWEEL_RE = re.compile(r"[\u0640]")
# Bidi / direction marks that can appear in extracted PDFs.
_BIDI_MARKS_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def normalize_text(text: str) -> str:
    """
    Normalize extracted text so chunking/search is more consistent.

    Rules (simple and safe for legal text):
    - Convert Windows newlines to \\n
    - Unicode normalize (NFKC) to reduce PDF "presentation forms" issues
    - Collapse repeated spaces/tabs
    - Collapse 3+ newlines to 2 newlines (preserve paragraph breaks)
    - Strip Arabic diacritics/tatweel and bidi marks (helps search)
    - Strip outer whitespace
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # NFKC converts many Arabic presentation form glyphs into standard letters.
    text = unicodedata.normalize("NFKC", text)
    text = _BIDI_MARKS_RE.sub("", text)
    text = _AR_TATWEEL_RE.sub("", text)
    text = _AR_DIACRITICS_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()
