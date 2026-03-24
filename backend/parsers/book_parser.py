"""
Book parser — supports PDF (pypdf) and EPUB (ebooklib).
Extracts full text and returns overlapping 2000-token chunks.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedBook:
    filename: str
    raw_text: str
    chunks: list[str] = field(default_factory=list)
    total_chars: int = 0


# ── helpers ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 8000, overlap: int = 800) -> list[str]:
    """Split text into overlapping chunks (chars, ~2000 tokens each)."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _clean(text: str) -> str:
    """Remove excessive whitespace while keeping paragraph breaks."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── PDF ───────────────────────────────────────────────────────────────────────

def _parse_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return _clean("\n\n".join(pages))


# ── EPUB ──────────────────────────────────────────────────────────────────────

def _parse_epub(data: bytes) -> str:
    import ebooklib
    from ebooklib import epub
    import html
    import tempfile
    import os

    # ebooklib requires a real file path — BytesIO not supported
    # Use mkstemp + explicit close so Windows releases the handle before ebooklib opens it
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".epub")
    try:
        os.write(tmp_fd, data)
        os.close(tmp_fd)
        book = epub.read_epub(tmp_path)
        parts: list[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content().decode("utf-8", errors="ignore")
            content = re.sub(r"<[^>]+>", " ", content)
            content = html.unescape(content)
            parts.append(content)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # Windows: file briefly locked, temp folder will clean it up

    return _clean("\n\n".join(parts))


# ── public API ────────────────────────────────────────────────────────────────

def parse_book(filename: str, data: bytes) -> ParsedBook:
    """Parse a PDF or EPUB file and return chunked text."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        raw_text = _parse_pdf(data)
    elif ext in (".epub",):
        raw_text = _parse_epub(data)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Only PDF and EPUB are supported.")

    chunks = _chunk_text(raw_text)
    return ParsedBook(
        filename=filename,
        raw_text=raw_text,
        chunks=chunks,
        total_chars=len(raw_text),
    )
