from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import DocumentStatus
from app.models.orm import Document, QaEntry, QaSourceLink
from app.rag import embedding
from app.rag.index import KnowledgeChunk, index_manager
from app.rag.qa_index import QaMatch, qa_index_manager
from app.rag.retrieval import RetrievalResult
from app.services.chat_scope import scope_hohai_query

TIME_SENSITIVE_MARKERS = (
    "最新",
    "现在",
    "当前",
    "今年",
    "明年",
    "近期",
    "本学期",
    "招生",
    "政策",
    "校历",
)
QUESTION_TRAILING_MARKS = re.compile(r"[\s?？!！。；;，,]+$")
SEMANTIC_REWRITES = (
    ("几个", "多少个"),
    ("多少个", "几个"),
    ("多少人", "人数"),
    ("人数", "多少人"),
    ("什么时候", "时间"),
    ("哪一年", "年份"),
)


def normalize_question(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower().strip()
    return "".join(character for character in normalized if character.isalnum())


def question_hash(value: str) -> str:
    return hashlib.sha256(normalize_question(value).encode("utf-8")).hexdigest()


def rewrite_qa_queries(value: str) -> tuple[str, ...]:
    """Create a small deterministic query set without an extra LLM call."""
    query = unicodedata.normalize("NFKC", value).strip()
    query = QUESTION_TRAILING_MARKS.sub("", query)
    query = scope_hohai_query(query)

    variants = [query]
    for source, target in SEMANTIC_REWRITES:
        if source not in query:
            continue
        rewritten = query.replace(source, target)
        if rewritten not in variants:
            variants.append(rewritten)
    return tuple(item for item in variants[:4] if item)


@dataclass(frozen=True, slots=True)
class QaResolvedSource:
    marker: str
    citation_index: int
    source_kind: str
    result: RetrievalResult
    original_marker: str = "S"
    original_citation_index: int = 1

    def source_dict(self) -> dict[str, object]:
        source = self.result.source_dict(citation_index=self.citation_index)
        source["source_type"] = (
            "WEB_ARCHIVE" if self.source_kind == "WEB_ARCHIVE" else self.result.document_kind
        )
        return source


@dataclass(frozen=True, slots=True)
class QaLookup:
    query_vector: np.ndarray | None
    mode: str
    match: QaMatch | None = None
    sources: tuple[QaResolvedSource, ...] = ()


class QaKnowledgeService:
    def lookup(self, query: str) -> QaLookup:
        if not settings.qa_retrieval_enabled:
            return QaLookup(None, "none")
        rewritten_queries = rewrite_qa_queries(query) or (query,)
        vectors = [embedding.embedder.embed_query(item) for item in rewritten_queries]
        vector = vectors[0]
        if qa_index_manager.count == 0:
            return QaLookup(vector, "none")
        best_matches: dict[int, QaMatch] = {}
        for candidate_vector in vectors:
            for match in qa_index_manager.search(candidate_vector, settings.qa_retrieval_top_k):
                current = best_matches.get(match.entry_id)
                if current is None or match.score > current.score:
                    best_matches[match.entry_id] = match
        matches = sorted(best_matches.values(), key=lambda item: item.score, reverse=True)
        if not matches:
            return QaLookup(vector, "none")

        top = matches[0]
        with SessionLocal() as db:
            entry = db.get(QaEntry, top.entry_id)
            if entry is None or not entry.is_active:
                return QaLookup(vector, "none")
            sources = self._resolve_sources(db, entry.id)
            if not sources:
                return QaLookup(vector, "none")
            updated_at = entry.updated_at

        exact = normalize_question(query) == normalize_question(top.question)
        second_score = matches[1].score if len(matches) > 1 else -1.0
        separated = top.score - second_score >= settings.qa_min_score_margin
        direct = top.score >= settings.qa_direct_min_score and (exact or separated)
        if direct and self._is_stale_time_sensitive(query, updated_at):
            direct = False
        if direct and self._references_are_resolved(top.answer, sources):
            return QaLookup(vector, "direct", top, tuple(sources))
        if top.score >= settings.qa_assist_min_score:
            return QaLookup(vector, "assist", top, tuple(sources))
        return QaLookup(vector, "none")

    @staticmethod
    def _resolve_sources(db, entry_id: int) -> list[QaResolvedSource]:  # type: ignore[no-untyped-def]
        links = db.scalars(
            select(QaSourceLink)
            .where(QaSourceLink.qa_entry_id == entry_id)
            .order_by(QaSourceLink.marker, QaSourceLink.citation_index)
        ).all()
        if not links:
            return []
        snapshot = index_manager.snapshot()
        first_record_by_document: dict[int, KnowledgeChunk] = {}
        for record in snapshot.records.values():
            first_record_by_document.setdefault(record.document_id, record)
        resolved: list[QaResolvedSource] = []
        seen_documents: set[int] = set()
        for link in links:
            if link.document_id in seen_documents:
                continue
            document = db.get(Document, link.document_id)
            if document is None or document.status != DocumentStatus.READY:
                continue
            record = snapshot.records.get(link.source_chunk_id or -1)
            if record is None or record.document_id != document.id:
                record = first_record_by_document.get(document.id)
            if record is None:
                continue
            seen_documents.add(document.id)
            resolved.append(
                QaResolvedSource(
                    marker="S",
                    citation_index=len(resolved) + 1,
                    source_kind=link.source_kind,
                    result=RetrievalResult(
                        chunk_id=record.chunk_id,
                        document_id=record.document_id,
                        title=record.title,
                        content=record.content,
                        source_url=record.source_url,
                        published_at=record.published_at,
                        score=1.0,
                        dense_rank=1,
                        sparse_rank=1,
                        lexical_coverage=1.0,
                        document_kind=record.document_kind,
                        contributor_name=record.contributor_name,
                    ),
                    original_marker=link.marker,
                    original_citation_index=link.citation_index,
                )
            )
        return resolved[: settings.context_top_k]

    @staticmethod
    def _references_are_resolved(answer: str, sources: list[QaResolvedSource]) -> bool:
        references = {
            (marker, int(index)) for marker, index in re.findall(r"\[([SW])(\d+)\]", answer)
        }
        available = {(source.original_marker, source.original_citation_index) for source in sources}
        return bool(references) and references.issubset(available)

    @staticmethod
    def _is_stale_time_sensitive(question: str, updated_at: datetime) -> bool:
        if not any(marker in question for marker in TIME_SENSITIVE_MARKERS):
            return False
        value = updated_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        age_days = (datetime.now(UTC) - value).days
        return age_days > settings.qa_time_sensitive_max_age_days


qa_knowledge_service = QaKnowledgeService()
