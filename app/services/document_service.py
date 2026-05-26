"""
Сервис извлечения текста из документов: PDF, DOCX, Markdown, TXT.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


async def extract_text(content: bytes, content_type: str, filename: str) -> str:
    """
    Извлекает текст из файла в зависимости от типа.
    Возвращает чистый текст.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if content_type == "application/pdf" or ext == "pdf":
        return _extract_pdf(content)
    elif content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or ext in ("docx", "doc"):
        return _extract_docx(content)
    elif content_type in ("text/markdown", "text/plain") or ext in ("md", "txt", "rst"):
        return content.decode("utf-8", errors="replace")
    else:
        # Попытка как текст
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            raise ValueError(f"Неподдерживаемый тип файла: {content_type} / .{ext}")


def _extract_pdf(content: bytes) -> str:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise ImportError("Установите pdfplumber: pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _extract_docx(content: bytes) -> str:
    try:
        import docx  # type: ignore
    except ImportError:
        raise ImportError("Установите python-docx: pip install python-docx")

    doc = docx.Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def estimate_tokens(text: str) -> int:
    """Грубая оценка: ~4 символа на токен."""
    return len(text) // 4
