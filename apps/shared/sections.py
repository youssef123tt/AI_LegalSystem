"""
Section parsing for legal documents (v1).

Milestone 6 goal:
- detect high-level structure like Article/Section/Chapter headings
- generate a section_path like ["Chapter 1", "Article 3", "Section 2"]

This is heuristic and designed to work on many US/EU texts; it can be
extended later for Arabic headings and jurisdiction-specific formats.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SectionSpan:
    section_path: list[str]
    start_char: int
    end_char: int
    heading: str


_CHAPTER_RE = re.compile(r"^\s*(CHAPTER)\s+([0-9IVXLC]+)\b", re.IGNORECASE)
_TITLE_RE = re.compile(r"^\s*(TITLE)\s+([0-9IVXLC]+)\b", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"^\s*(ARTICLE)\s+([0-9IVXLC]+)\b", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*(SECTION)\s+([0-9A-Za-z][0-9A-Za-z\.\-]*)\b", re.IGNORECASE)
_PARA_SECTION_RE = re.compile(r"^\s*§+\s*([0-9A-Za-z][0-9A-Za-z\.\-]*)\b")


def parse_section_spans(text: str) -> list[SectionSpan]:
    """
    Return a list of section spans covering the document.

    If no headings are found, returns a single span with section_path=[].
    """
    if not text:
        return []

    lines = text.split("\n")
    offsets: list[int] = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1  # +1 for '\n'

    headers: list[tuple[int, int, str, int]] = []
    # tuple: (start_char, level, label, line_index)
    for i, ln in enumerate(lines):
        start = offsets[i]
        stripped = ln.strip()
        if not stripped:
            continue

        m = _TITLE_RE.match(ln)
        if m:
            label = f"Title {m.group(2)}"
            headers.append((start, 0, label, i))
            continue

        m = _CHAPTER_RE.match(ln)
        if m:
            label = f"Chapter {m.group(2)}"
            headers.append((start, 1, label, i))
            continue

        m = _ARTICLE_RE.match(ln)
        if m:
            label = f"Article {m.group(2)}"
            headers.append((start, 2, label, i))
            continue

        m = _SECTION_RE.match(ln)
        if m:
            label = f"Section {m.group(2)}"
            headers.append((start, 3, label, i))
            continue

        m = _PARA_SECTION_RE.match(ln)
        if m:
            label = f"Section {m.group(1)}"
            headers.append((start, 3, label, i))
            continue

    if not headers:
        return [SectionSpan(section_path=[], start_char=0, end_char=len(text), heading="")]

    headers.sort(key=lambda x: x[0])

    spans: list[SectionSpan] = []
    stack: list[str] = []
    stack_levels: list[int] = []

    def set_level(level: int, label: str):
        nonlocal stack, stack_levels
        # Pop to < level
        while stack_levels and stack_levels[-1] >= level:
            stack.pop()
            stack_levels.pop()
        stack.append(label)
        stack_levels.append(level)

    for idx, (start, level, label, _line_i) in enumerate(headers):
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(text)
        set_level(level, label)
        spans.append(
            SectionSpan(
                section_path=list(stack),
                start_char=start,
                end_char=end,
                heading=label,
            )
        )

    # If the first header does not start at 0, include a preface span.
    if spans and spans[0].start_char > 0:
        spans.insert(0, SectionSpan(section_path=[], start_char=0, end_char=spans[0].start_char, heading=""))

    return spans

