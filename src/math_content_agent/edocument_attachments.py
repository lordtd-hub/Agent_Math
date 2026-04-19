"""Attachment download and extraction helpers for eDocument digests."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from openpyxl import load_workbook
from pypdf import PdfReader

_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _truncate_lines(lines: list[str], max_lines: int = 4, max_chars: int = 600) -> str:
    kept: list[str] = []
    total = 0
    for line in lines:
        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if cleaned in kept:
            continue
        kept.append(cleaned)
        total += len(cleaned)
        if len(kept) >= max_lines or total >= max_chars:
            break
    return " | ".join(kept)[:max_chars]


def extract_pdf_preview(path: Path) -> str:
    """Extract a short textual preview from a PDF file."""

    reader = PdfReader(str(path))
    lines: list[str] = []
    for page in reader.pages[:3]:
        text = page.extract_text() or ""
        lines.extend(text.splitlines())
    return _truncate_lines(lines)


def extract_docx_preview(path: Path) -> str:
    """Extract a short textual preview from a DOCX file."""

    document = DocxDocument(str(path))
    lines = [paragraph.text for paragraph in document.paragraphs]
    return _truncate_lines(lines)


def extract_xlsx_preview(path: Path) -> str:
    """Extract a short textual preview from an Excel workbook."""

    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets[:2]:
        lines.append(f"Sheet: {sheet.title}")
        for row in sheet.iter_rows(max_row=6, values_only=True):
            values = [str(cell).strip() for cell in row if cell not in (None, "")]
            if values:
                lines.append(" | ".join(values))
        if len(lines) >= 8:
            break
    return _truncate_lines(lines, max_lines=6, max_chars=700)


def extract_attachment_preview(path: Path) -> str:
    """Dispatch preview extraction by file extension."""

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_preview(path)
    if suffix == ".docx":
        return extract_docx_preview(path)
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return extract_xlsx_preview(path)
    if suffix in {".csv", ".tsv"}:
        return _truncate_lines(path.read_text(encoding="utf-8", errors="ignore").splitlines(), max_lines=6, max_chars=700)
    raise ValueError(f"Unsupported attachment type: {suffix or 'unknown'}")
