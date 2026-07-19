from __future__ import annotations

import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.core.config import settings

from . import embedding
from .index import IndexManager, index_manager, tokenize

logger = logging.getLogger("uvicorn.error")

LEXICAL_STOPWORDS = {
    "什么",
    "怎么",
    "如何",
    "多少",
    "一下",
    "请问",
    "等于",
    "的",
    "了",
    "吗",
    "呢",
    "是",
    "几",
    "做",
}


def lexical_coverage(query: str, content: str) -> float:
    """Measure meaningful query-token coverage in a retrieved chunk."""
    normalized_query = query.replace("等于", "=").replace("＝", "=")
    normalized_content = content.replace("等于", "=").replace("＝", "=")

    def meaningful(text: str) -> set[str]:
        return {
            token
            for token in tokenize(text)
            if token not in LEXICAL_STOPWORDS
            and (token.isalnum() or len(token) > 1 or token in {"+", "-", "*", "/", "="})
        }

    query_tokens = meaningful(normalized_query)
    if not query_tokens:
        return 0.0
    content_tokens = meaningful(normalized_content)
    return len(query_tokens & content_tokens) / len(query_tokens)


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: int
    document_id: int
    title: str
    content: str
    source_url: str | None
    published_at: date | None
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None
    lexical_coverage: float = 0.0
    document_kind: str = "KNOWLEDGE_BASE"
    contributor_name: str | None = None

    def source_dict(self, citation_index: int | None = None) -> dict[str, object]:
        snippet = self.content[:360] + ("…" if len(self.content) > 360 else "")
        source = {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "score": round(self.score, 4),
            "snippet": snippet,
            "contributor_name": self.contributor_name,
        }
        if citation_index is not None:
            source["citation_index"] = citation_index
        return source


class LocalReranker:
    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self._inference_lock = threading.Lock()

    def _load(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder

                    self._model = CrossEncoder(
                        settings.reranker_model,
                        device=None if settings.model_device == "auto" else settings.model_device,
                        local_files_only=settings.model_local_files_only,
                        max_length=settings.reranker_max_length,
                    )
        return self._model

    def scores(self, query: str, contents: list[str]) -> list[float]:
        with self._inference_lock:
            raw = self._load().predict([(query, content) for content in contents])
        return [1.0 / (1.0 + math.exp(-float(value))) for value in raw]


class RetrievalService:
    def __init__(
        self,
        manager: IndexManager = index_manager,
        reranker: LocalReranker | None = None,
    ) -> None:
        self.manager = manager
        self.reranker = reranker or LocalReranker()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="retrieval")

    def warmup(self) -> None:
        """Load local models before the server accepts its first chat request."""
        snapshot = self.manager.snapshot()
        if snapshot.count == 0:
            return
        started = time.perf_counter()
        embedding.embedder.embed_query("河海大学")
        if settings.rerank_enabled:
            first_record = snapshot.records[snapshot.chunk_ids[0]]
            self.reranker.scores("河海大学", [first_record.content])
        logger.info("RAG local models warmed in %.2fs", time.perf_counter() - started)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        *,
        query_vector: np.ndarray | None = None,
        use_sparse: bool = True,
        use_rerank: bool | None = None,
    ) -> list[RetrievalResult]:
        started = time.perf_counter()
        vector = query_vector if query_vector is not None else embedding.embedder.embed_query(query)
        embedded_at = time.perf_counter()
        dense_future = self._pool.submit(self.manager.dense_search, vector, settings.dense_top_k)
        sparse_future = (
            self._pool.submit(self.manager.sparse_search, query, settings.sparse_top_k)
            if use_sparse
            else None
        )
        dense = dense_future.result()
        sparse = sparse_future.result() if sparse_future else []
        dense_ranks = {chunk_id: rank for rank, (chunk_id, _score) in enumerate(dense, start=1)}
        sparse_ranks = {chunk_id: rank for rank, (chunk_id, _score) in enumerate(sparse, start=1)}
        fused = self._rrf(dense, sparse)[: settings.fusion_top_k]
        if not fused:
            return []

        by_id = self.manager.records([chunk_id for chunk_id, _score in fused])
        candidates = [
            (chunk_id, by_id[chunk_id], score) for chunk_id, score in fused if chunk_id in by_id
        ]

        should_rerank = settings.rerank_enabled if use_rerank is None else use_rerank
        if should_rerank and candidates:
            candidates = candidates[: settings.rerank_candidate_k]
            rerank_scores = self.reranker.scores(query, [item[1].content for item in candidates])
            candidates = [
                (chunk_id, record, rerank_score)
                for (chunk_id, record, _score), rerank_score in zip(
                    candidates, rerank_scores, strict=False
                )
            ]
            candidates.sort(key=lambda item: item[2], reverse=True)

        deduplicated = []
        seen_documents: set[int] = set()
        for candidate in candidates:
            document_id = candidate[1].document_id
            if document_id in seen_documents:
                continue
            seen_documents.add(document_id)
            deduplicated.append(candidate)
        candidates = deduplicated

        logger.info(
            "RAG retrieval completed query_embedding=%.2fs total=%.2fs candidates=%d "
            "rerank=%s top_document=%s top_score=%.4f",
            embedded_at - started,
            time.perf_counter() - started,
            len(candidates),
            should_rerank,
            candidates[0][1].document_id if candidates else None,
            candidates[0][2] if candidates else 0.0,
        )

        limit = top_k or settings.context_top_k
        return [
            RetrievalResult(
                chunk_id=chunk_id,
                document_id=record.document_id,
                title=record.title,
                content=record.content,
                source_url=record.source_url,
                published_at=record.published_at,
                score=float(score),
                dense_rank=dense_ranks.get(chunk_id),
                sparse_rank=sparse_ranks.get(chunk_id),
                lexical_coverage=lexical_coverage(query, record.content),
                document_kind=record.document_kind,
                contributor_name=record.contributor_name,
            )
            for chunk_id, record, score in candidates[:limit]
        ]

    @staticmethod
    def _rrf(*rankings: list[tuple[int, float]]) -> list[tuple[int, float]]:
        scores: dict[int, float] = {}
        dense_scores: dict[int, float] = dict(rankings[0]) if rankings else {}
        for ranking in rankings:
            for rank, (chunk_id, _raw_score) in enumerate(ranking, start=1):
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (settings.rrf_k + rank)
        ordered = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
        # Before reranking, expose cosine score when available; otherwise normalized RRF.
        max_rrf = max(scores.values(), default=1.0)
        return [
            (chunk_id, dense_scores.get(chunk_id, scores[chunk_id] / max_rrf))
            for chunk_id in ordered
        ]


retrieval_service = RetrievalService()
