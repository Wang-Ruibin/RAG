from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import settings

from .parser import ParsedDocument


@dataclass(slots=True)
class ChunkDraft:
    content: str
    ordinal: int
    heading_path: str = ""
    page_number: int | None = None


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= size:
        return [text] if text else []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        carry = current[-overlap:] if current and overlap else ""
        current = f"{carry}\n{paragraph}".strip()
        while len(current) > size:
            cut = max(current.rfind(mark, 0, size) for mark in ("。", "！", "？", "；", "，", "\n"))
            if cut < size // 2:
                cut = size
            else:
                cut += 1
            piece = current[:cut].strip()
            if piece:
                chunks.append(piece)
            current = current[max(0, cut - overlap) :].strip()
    if current:
        chunks.append(current)
    return chunks


def chunk_document(parsed: ParsedDocument) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    ordinal = 0
    for section in parsed.sections:
        for piece in _split_text(section.text, settings.chunk_size, settings.chunk_overlap):
            prefix = (
                f"{parsed.title}\n{section.heading_path}\n"
                if section.heading_path
                else f"{parsed.title}\n"
            )
            drafts.append(
                ChunkDraft(
                    content=(prefix + piece).strip(),
                    ordinal=ordinal,
                    heading_path=section.heading_path,
                    page_number=section.page_number,
                )
            )
            ordinal += 1
    return drafts
