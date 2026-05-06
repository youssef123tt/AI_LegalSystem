"""
Text extraction helpers.
"""

from __future__ import annotations

import os
from pathlib import Path


class ExtractionError(RuntimeError):
    pass


def extract_text_from_file(path: str) -> tuple[str, str]:
    text, method, _ = extract_text_with_metadata(path)
    return text, method


def extract_text_with_metadata(path: str) -> tuple[str, str, dict | None]:
    """
    Extract text and return (text, extraction_method, page_map_json).
    page_map_json is currently available for PDF extraction/OCR.
    """
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".pdf":
        text, method, page_map = _extract_pdf_text_with_page_map(path)
        return text, method, page_map
    if suffix == ".docx":
        return _extract_docx_text(path), "docx_text", None
    if suffix in (".txt", ".md"):
        return p.read_text(encoding="utf-8", errors="replace"), "plain_text", None

    raise ExtractionError(f"Unsupported file type: {suffix or '(no extension)'}")


def audit_pdf_tounicode(path: str) -> bool | None:
    """
    Best-effort check: do PDF fonts include ToUnicode maps?
    """
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        any_fonts = False
        any_tounicode = False
        for page in reader.pages[:5]:
            resources = page.get("/Resources") or {}
            fonts = (resources.get("/Font") or {}) if isinstance(resources, dict) else {}
            if not isinstance(fonts, dict):
                continue
            for _, font_ref in fonts.items():
                any_fonts = True
                try:
                    font = font_ref.get_object()
                    if isinstance(font, dict) and "/ToUnicode" in font:
                        any_tounicode = True
                        break
                except Exception:
                    continue
            if any_tounicode:
                break
        if not any_fonts:
            return None
        return any_tounicode
    except Exception:
        return None


def _build_page_map(page_texts: list[str]) -> tuple[str, dict]:
    """
    Build full text and page map (char offsets in the full text).
    """
    full_parts: list[str] = []
    pages: list[dict] = []
    cursor = 0

    for i, raw in enumerate(page_texts, start=1):
        page_text = raw or ""
        if full_parts:
            full_parts.append("\n\n")
            cursor += 2
        start = cursor
        full_parts.append(page_text)
        cursor += len(page_text)
        pages.append(
            {
                "page": i,
                "char_start": start,
                "char_end": cursor,
                "char_count": len(page_text),
            }
        )

    return "".join(full_parts), {"pages": pages}


def _extract_pdf_text_with_page_map(path: str) -> tuple[str, str, dict | None]:
    """
    Try multiple PDF extractors and pick the highest quality candidate.
    """
    candidates: list[tuple[str, list[str]]] = []

    # 1) pdfplumber.
    try:
        import pdfplumber  # type: ignore

        page_texts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_texts.append(page.extract_text() or "")
        if any(t.strip() for t in page_texts):
            candidates.append(("pdfplumber", page_texts))
    except Exception:
        pass

    # 2) PyMuPDF.
    try:
        import fitz  # type: ignore

        doc = fitz.open(path)
        page_texts = []
        for page in doc:
            page_texts.append(page.get_text("text") or "")
        doc.close()
        if any(t.strip() for t in page_texts):
            candidates.append(("pymupdf", page_texts))
    except Exception:
        pass

    # 3) pypdf.
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        page_texts = []
        for page in reader.pages:
            page_texts.append(page.extract_text() or "")
        if any(t.strip() for t in page_texts):
            candidates.append(("pypdf", page_texts))
    except Exception:
        pass

    if not candidates:
        raise ExtractionError("PDF extraction failed: no extractor produced text")

    scored: list[tuple[int, str, list[str]]] = []
    for method, page_texts in candidates:
        full_text, _ = _build_page_map(page_texts)
        scored.append((_quality_score(full_text), method, page_texts))

    _, method, best_pages = max(scored, key=lambda x: x[0])
    text, page_map = _build_page_map(best_pages)
    return text, method, page_map


def _quality_score(text: str) -> int:
    if not text:
        return -(10**9)

    base_ar = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
    ascii_letters = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    pres_a = sum(1 for ch in text if "\uFB50" <= ch <= "\uFDFF")
    pres_b = sum(1 for ch in text if "\uFE70" <= ch <= "\uFEFF")
    pres = pres_a + pres_b
    repl = text.count("\ufffd")
    length = len(text)

    return (base_ar * 3) + (ascii_letters * 2) + min(length, 50000) - (pres * 6) - (repl * 50)


def quality_score_for_text(text: str) -> int:
    return int(_quality_score(text))


def extract_pdf_ocr(path: str) -> str:
    text, _metrics = extract_pdf_ocr_with_metrics(path)
    return text


def extract_pdf_ocr_with_metrics(path: str) -> tuple[str, dict]:
    """
    Extract text with OCR and return (text, metrics).
    Metrics include avg confidence and page map.
    """
    try:
        from pdf2image import convert_from_path  # type: ignore
        from PIL import ImageOps  # type: ignore
        import pytesseract  # type: ignore
    except ImportError as e:
        raise ExtractionError(f"OCR dependencies missing: {e}") from e

    dpi = int(os.getenv("OCR_DPI", "300"))
    langs = os.getenv("OCR_LANGS", "ara+eng")

    images = convert_from_path(path, dpi=dpi)
    page_texts: list[str] = []
    conf_values: list[float] = []

    for img in images:
        gray = ImageOps.grayscale(img)
        proc = ImageOps.autocontrast(gray)

        page_text = pytesseract.image_to_string(proc, lang=langs)
        page_texts.append(page_text)

        data = pytesseract.image_to_data(
            proc,
            lang=langs,
            output_type=pytesseract.Output.DICT,
        )
        for c in data.get("conf", []):
            try:
                v = float(c)
            except Exception:
                continue
            if v >= 0:
                conf_values.append(v)

    text, page_map = _build_page_map(page_texts)
    avg_conf = (sum(conf_values) / len(conf_values)) if conf_values else 0.0
    metrics = {
        "pages": len(images),
        "avg_confidence": round(avg_conf, 2),
        "page_map": page_map,
    }
    return text, metrics


def _extract_docx_text(path: str) -> str:
    try:
        import docx  # type: ignore

        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs if p.text and p.text.strip()]
        return "\n\n".join(paras)
    except Exception as exc:
        raise ExtractionError(f"DOCX extraction failed: {exc}") from exc

