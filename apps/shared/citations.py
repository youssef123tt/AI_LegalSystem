"""
Legal citation extraction (rule-based v2).

Conservative patterns for auditability and deterministic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CitationMatch:
    raw_text: str
    canonical_id: str
    citation_type: str
    jurisdiction: str | None
    start_char: int
    end_char: int
    display: str | None = None
    official_url: str | None = None


_USC_RE = re.compile(
    r"\b(?P<title>\d{1,3})\s*(?:U\.?\s*S\.?\s*C\.?|USC)\s*(?:§+|Sec\.?|Section)?\s*(?P<section>[\w\.\-\(\)]+)",
    re.IGNORECASE,
)
_CFR_RE = re.compile(
    r"\b(?P<title>\d{1,3})\s*(?:C\.?\s*F\.?\s*R\.?|CFR)\s*(?:§+|Part)?\s*(?P<section>[\w\.\-]+)",
    re.IGNORECASE,
)
_CASE_RE = re.compile(
    r"\b(?P<a>[A-Z][A-Za-z&\.\-']{1,40})\s+v\.?\s+(?P<b>[A-Z][A-Za-z&\.\-']{1,40})(?:\s*\((?P<year>\d{4})\))?",
)

# Egyptian law references: "القانون رقم 14 لسنة 2025"
_EG_LAW_RE = re.compile(r"(?:القانون|قانون)\s+رقم\s+(?P<num>\d+)\s+لسنة\s+(?P<year>\d{4})")

# EU references.
_EU_REG_RE = re.compile(
    r"\bRegulation\s*\(?(?:EU|EC)\)?\s*(?P<year>\d{4})/(?P<num>\d{1,5})\b",
    re.IGNORECASE,
)
_EU_DIR_RE = re.compile(
    r"\bDirective\s*\(?(?:EU|EC)\)?\s*(?P<year>\d{4})/(?P<num>\d{1,5})\b",
    re.IGNORECASE,
)

# Article references.
_AR_ARTICLE_RE = re.compile(r"المادة\s*\(?\s*(?P<num>\d+)\s*\)?")
_EN_ARTICLE_RE = re.compile(r"\b(?P<kind>Article|Section)\s+(?P<num>\d+[A-Za-z0-9\-\.]*)\b")


def _official_url_for(citation_type: str, canonical_id: str) -> str | None:
    parts = canonical_id.split(":")
    try:
        if citation_type == "usc" and len(parts) >= 4:
            title, section = parts[2], parts[3]
            return f"https://www.law.cornell.edu/uscode/text/{title}/{section}"
        if citation_type == "cfr" and len(parts) >= 4:
            title, section = parts[2], parts[3]
            return f"https://www.ecfr.gov/current/title-{title}/section-{section}"
        if citation_type == "eu_reg" and len(parts) >= 4:
            year, num = parts[2], parts[3]
            return f"https://eur-lex.europa.eu/eli/reg/{year}/{num}/oj"
        if citation_type == "eu_dir" and len(parts) >= 4:
            year, num = parts[2], parts[3]
            return f"https://eur-lex.europa.eu/eli/dir/{year}/{num}/oj"
    except Exception:
        return None
    return None


def extract_citations(text: str, *, default_jurisdiction: str | None = None) -> list[CitationMatch]:
    if not text:
        return []

    out: list[CitationMatch] = []

    def add(
        m: re.Match,
        *,
        canonical_id: str,
        citation_type: str,
        jurisdiction: str | None,
        display: str | None = None,
    ):
        raw = m.group(0)
        start, end = m.span(0)
        out.append(
            CitationMatch(
                raw_text=raw,
                canonical_id=canonical_id,
                citation_type=citation_type,
                jurisdiction=jurisdiction,
                start_char=start,
                end_char=end,
                display=display or raw,
                official_url=_official_url_for(citation_type, canonical_id),
            )
        )

    for m in _USC_RE.finditer(text):
        title = m.group("title")
        section = m.group("section").strip()
        canonical = f"us:usc:{title}:{section.lower()}"
        add(m, canonical_id=canonical, citation_type="usc", jurisdiction="US")

    for m in _CFR_RE.finditer(text):
        title = m.group("title")
        section = m.group("section").strip()
        canonical = f"us:cfr:{title}:{section.lower()}"
        add(m, canonical_id=canonical, citation_type="cfr", jurisdiction="US")

    for m in _CASE_RE.finditer(text):
        a = m.group("a").lower()
        b = m.group("b").lower()
        year = m.group("year") or ""
        canonical = f"us:case:{a}_v_{b}:{year}"
        add(m, canonical_id=canonical, citation_type="case", jurisdiction="US")

    for m in _EG_LAW_RE.finditer(text):
        num = m.group("num")
        year = m.group("year")
        canonical = f"eg:law:{year}:{num}"
        add(m, canonical_id=canonical, citation_type="eg_law", jurisdiction="EG")

    for m in _EU_REG_RE.finditer(text):
        year = m.group("year")
        num = m.group("num")
        canonical = f"eu:reg:{year}:{num}"
        add(m, canonical_id=canonical, citation_type="eu_reg", jurisdiction="EU")

    for m in _EU_DIR_RE.finditer(text):
        year = m.group("year")
        num = m.group("num")
        canonical = f"eu:dir:{year}:{num}"
        add(m, canonical_id=canonical, citation_type="eu_dir", jurisdiction="EU")

    for m in _AR_ARTICLE_RE.finditer(text):
        num = m.group("num")
        canonical = f"ref:article:{num}"
        add(m, canonical_id=canonical, citation_type="article_ref", jurisdiction=default_jurisdiction)

    for m in _EN_ARTICLE_RE.finditer(text):
        kind = m.group("kind").lower()
        num = m.group("num").lower()
        canonical = f"ref:{kind}:{num}"
        add(m, canonical_id=canonical, citation_type=f"{kind}_ref", jurisdiction=default_jurisdiction)

    seen: set[tuple[str, int, int]] = set()
    deduped: list[CitationMatch] = []
    for c in out:
        k = (c.canonical_id, c.start_char, c.end_char)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(c)
    return deduped

