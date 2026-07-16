from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import faiss
import jieba
import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings

from .chunker import ChunkDraft

KNOWLEDGE_SCHEMA_VERSION = 1
logger = logging.getLogger("uvicorn.error")


def tokenize(text: str) -> list[str]:
    return [token.strip().lower() for token in jieba.lcut(text) if token.strip()]


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """A retrievable knowledge record loaded from the standalone knowledge base."""

    chunk_id: int
    document_id: int
    ordinal: int
    title: str
    content: str
    category: str
    source_url: str | None
    published_at: date | None
    heading_path: str | None
    page_number: int | None
    token_count: int


@dataclass(frozen=True, slots=True)
class IndexSnapshot:
    dense: faiss.IndexIDMap2 | None
    bm25: BM25Okapi | None
    chunk_ids: tuple[int, ...]
    records: dict[int, KnowledgeChunk]
    count: int


class IndexManager:
    """Own the standalone knowledge base and immutable retrieval snapshots.

    MySQL/SQLite contains only business metadata. Source text and embeddings are
    atomically stored per document in ``data/knowledge_base/documents/*.npz``.
    FAISS and BM25 are derived indexes that can always be rebuilt from those files.
    """

    def __init__(self) -> None:
        self._snapshot_lock = threading.RLock()
        self._mutation_lock = threading.RLock()
        self._snapshot = IndexSnapshot(None, None, (), {}, 0)

    @property
    def count(self) -> int:
        with self._snapshot_lock:
            return self._snapshot.count

    def snapshot(self) -> IndexSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    @staticmethod
    def stable_chunk_id(document_id: int, ordinal: int) -> int:
        if document_id <= 0 or document_id >= 2**31:
            raise ValueError("document_id 超出知识库稳定 ID 范围")
        if ordinal < 0 or ordinal >= 2**32:
            raise ValueError("chunk ordinal 超出知识库稳定 ID 范围")
        return (document_id << 32) | ordinal

    def artifact_path(self, document_id: int) -> Path:
        return settings.knowledge_artifact_dir / f"{document_id}.npz"

    def upsert_document(
        self,
        *,
        document_id: int,
        title: str,
        category: str,
        source_url: str | None,
        published_at: date | None,
        drafts: list[ChunkDraft],
        vectors: np.ndarray,
        embedding_model: str,
        rebuild: bool = True,
    ) -> int:
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(drafts) or not drafts:
            raise ValueError("知识块与向量数量不一致")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("Embedding 包含非有限数值")

        chunk_ids = np.asarray(
            [self.stable_chunk_id(document_id, draft.ordinal) for draft in drafts],
            dtype=np.int64,
        )
        payload = {
            "schema_version": KNOWLEDGE_SCHEMA_VERSION,
            "document_id": document_id,
            "title": title,
            "category": category,
            "source_url": source_url,
            "published_at": published_at.isoformat() if published_at else None,
            "embedding_model": embedding_model,
            "dimension": int(matrix.shape[1]),
            "chunks": [
                {
                    "ordinal": draft.ordinal,
                    "content": draft.content,
                    "heading_path": draft.heading_path or None,
                    "page_number": draft.page_number,
                    "token_count": max(1, len(draft.content) // 2),
                }
                for draft in drafts
            ],
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        target = self.artifact_path(document_id)
        temp = Path(f"{target}.tmp")

        with self._mutation_lock:
            settings.ensure_directories()
            self._write_artifact(temp, target, chunk_ids, matrix, payload_bytes)
            if rebuild:
                self._rebuild_unlocked()
        return len(drafts)

    def update_document_metadata(
        self,
        document_id: int,
        *,
        title: str,
        category: str,
        source_url: str | None,
        published_at: date | None,
    ) -> bool:
        """Update knowledge metadata without recomputing unchanged embeddings."""
        with self._mutation_lock:
            target = self.artifact_path(document_id)
            if not target.exists():
                return False
            with np.load(target, allow_pickle=False) as archive:
                chunk_ids = np.asarray(archive["chunk_ids"], dtype=np.int64)
                vectors = np.asarray(archive["embeddings"], dtype=np.float32)
                payload = json.loads(archive["payload"].tobytes().decode("utf-8"))
            payload.update(
                {
                    "title": title,
                    "category": category,
                    "source_url": source_url,
                    "published_at": published_at.isoformat() if published_at else None,
                }
            )
            temp = Path(f"{target}.tmp")
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._write_artifact(temp, target, chunk_ids, vectors, payload_bytes)
            self._rebuild_unlocked()
            return True

    @staticmethod
    def _write_artifact(
        temp: Path,
        target: Path,
        chunk_ids: np.ndarray,
        vectors: np.ndarray,
        payload_bytes: bytes,
    ) -> None:
        with temp.open("wb") as handle:
            np.savez_compressed(
                handle,
                chunk_ids=chunk_ids,
                embeddings=vectors,
                payload=np.frombuffer(payload_bytes, dtype=np.uint8),
            )
        os.replace(temp, target)

    def delete_document(self, document_id: int, *, rebuild: bool = True) -> bool:
        with self._mutation_lock:
            target = self.artifact_path(document_id)
            existed = target.exists()
            if existed:
                target.unlink()
            if rebuild:
                self._rebuild_unlocked()
            return existed

    def rebuild(self) -> int:
        with self._mutation_lock:
            return self._rebuild_unlocked()

    def load(self, *, valid_document_ids: Collection[int] | None = None) -> int:
        """Load the persisted FAISS index and rebuild only the in-memory BM25 view.

        Per-document NPZ artifacts remain the source of truth. If the derived
        index is missing, stale, or corrupt, recover by rebuilding it from those
        artifacts. When database document IDs are supplied at application
        startup, artifacts left behind by interrupted legacy deletions are
        removed before the index is loaded.
        """
        with self._mutation_lock:
            if valid_document_ids is not None:
                valid_ids = {int(value) for value in valid_document_ids}
                removed = []
                for artifact in settings.knowledge_artifact_dir.glob("*.npz"):
                    try:
                        document_id = int(artifact.stem)
                    except ValueError:
                        continue
                    if document_id not in valid_ids:
                        artifact.unlink()
                        removed.append(document_id)
                if removed:
                    logger.warning(
                        "Removed orphaned knowledge artifacts document_ids=%s",
                        ",".join(str(value) for value in sorted(removed)),
                    )
            try:
                return self._load_persisted_unlocked()
            except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
                logger.warning("Persisted index unavailable; rebuilding from artifacts: %s", exc)
                return self._rebuild_unlocked()

    def _load_persisted_unlocked(self) -> int:
        settings.ensure_directories()
        index_path = settings.index_dir / "faiss.index"
        manifest_path = settings.index_dir / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError("index manifest is missing")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != KNOWLEDGE_SCHEMA_VERSION:
            raise ValueError("index schema version does not match")

        expected_count = int(manifest.get("count", -1))
        artifacts = sorted(settings.knowledge_artifact_dir.glob("*.npz"))
        if int(manifest.get("document_count", len(artifacts))) != len(artifacts):
            raise ValueError("document artifact count changed")

        if expected_count == 0:
            if artifacts:
                raise ValueError("empty index has document artifacts")
            with self._snapshot_lock:
                self._snapshot = IndexSnapshot(None, None, (), {}, 0)
            return 0

        if not index_path.is_file():
            raise ValueError("FAISS index is missing")
        latest_artifact = max((path.stat().st_mtime_ns for path in artifacts), default=0)
        if latest_artifact > index_path.stat().st_mtime_ns:
            raise ValueError("document artifacts are newer than the FAISS index")

        dense = faiss.read_index(str(index_path))
        if not isinstance(dense, faiss.IndexIDMap2):
            raise ValueError("persisted FAISS index has an unexpected type")
        if dense.ntotal != expected_count:
            raise ValueError("persisted FAISS vector count does not match manifest")

        records: dict[int, KnowledgeChunk] = {}
        models: set[str] = set()
        dimensions: set[int] = set()
        for artifact in artifacts:
            artifact_records, model, dimension = self._load_artifact_records(artifact)
            duplicate = records.keys() & artifact_records.keys()
            if duplicate:
                raise ValueError(f"duplicate chunk ID: {min(duplicate)}")
            records.update(artifact_records)
            models.add(model)
            dimensions.add(dimension)

        if len(records) != expected_count:
            raise ValueError("document chunk count does not match manifest")
        if models != {str(manifest.get("embedding_model"))}:
            raise ValueError("embedding model does not match manifest")
        if dimensions != {int(manifest.get("dimension", -1))} or dense.d not in dimensions:
            raise ValueError("embedding dimension does not match manifest")

        chunk_ids = tuple(sorted(records))
        persisted_ids = tuple(sorted(int(value) for value in faiss.vector_to_array(dense.id_map)))
        if persisted_ids != chunk_ids:
            raise ValueError("FAISS vector IDs do not match document artifacts")

        ordered_records = {chunk_id: records[chunk_id] for chunk_id in chunk_ids}
        corpus = [tokenize(ordered_records[chunk_id].content) or [""] for chunk_id in chunk_ids]
        snapshot = IndexSnapshot(
            dense=dense,
            bm25=BM25Okapi(corpus),
            chunk_ids=chunk_ids,
            records=ordered_records,
            count=len(ordered_records),
        )
        with self._snapshot_lock:
            self._snapshot = snapshot
        return snapshot.count

    def _rebuild_unlocked(self) -> int:
        settings.ensure_directories()
        records: dict[int, KnowledgeChunk] = {}
        ids_parts: list[np.ndarray] = []
        vector_parts: list[np.ndarray] = []
        models: set[str] = set()
        dimensions: set[int] = set()

        for artifact in sorted(settings.knowledge_artifact_dir.glob("*.npz")):
            artifact_records, chunk_ids, vectors, model = self._load_artifact(artifact)
            duplicate = records.keys() & artifact_records.keys()
            if duplicate:
                raise ValueError(f"知识库中存在重复 chunk ID: {min(duplicate)}")
            records.update(artifact_records)
            ids_parts.append(chunk_ids)
            vector_parts.append(vectors)
            models.add(model)
            dimensions.add(int(vectors.shape[1]))

        if not records:
            with self._snapshot_lock:
                self._snapshot = IndexSnapshot(None, None, (), {}, 0)
            self._persist_empty()
            return 0
        if len(models) != 1 or len(dimensions) != 1:
            raise ValueError("知识库文档使用了不一致的 Embedding 模型或维度，请全量重建")

        chunk_ids = np.concatenate(ids_parts).astype(np.int64, copy=False)
        vectors = np.vstack(vector_parts).astype(np.float32, copy=False)
        order = np.argsort(chunk_ids)
        chunk_ids = chunk_ids[order]
        vectors = vectors[order]
        ordered_records = {int(chunk_id): records[int(chunk_id)] for chunk_id in chunk_ids}
        dimension = int(vectors.shape[1])
        dense = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))
        dense.add_with_ids(vectors, chunk_ids)
        corpus = [tokenize(ordered_records[int(value)].content) or [""] for value in chunk_ids]
        bm25 = BM25Okapi(corpus)
        snapshot = IndexSnapshot(
            dense=dense,
            bm25=bm25,
            chunk_ids=tuple(int(value) for value in chunk_ids.tolist()),
            records=ordered_records,
            count=len(ordered_records),
        )
        self._persist(dense, len(records), dimension, next(iter(models)))
        with self._snapshot_lock:
            self._snapshot = snapshot
        return len(records)

    def _load_artifact(
        self, path: Path
    ) -> tuple[dict[int, KnowledgeChunk], np.ndarray, np.ndarray, str]:
        with np.load(path, allow_pickle=False) as archive:
            chunk_ids = np.asarray(archive["chunk_ids"], dtype=np.int64)
            vectors = np.asarray(archive["embeddings"], dtype=np.float32)
            payload = json.loads(archive["payload"].tobytes().decode("utf-8"))
        chunks = payload.get("chunks", [])
        if payload.get("schema_version") != KNOWLEDGE_SCHEMA_VERSION:
            raise ValueError(f"不支持的知识库格式: {path.name}")
        if vectors.ndim != 2 or len(chunks) != len(chunk_ids) or len(chunk_ids) != len(vectors):
            raise ValueError(f"知识库文件损坏或数量不一致: {path.name}")
        if int(payload.get("dimension", -1)) != int(vectors.shape[1]):
            raise ValueError(f"知识库向量维度不一致: {path.name}")

        published = payload.get("published_at")
        published_at = date.fromisoformat(published) if published else None
        document_id = int(payload["document_id"])
        result: dict[int, KnowledgeChunk] = {}
        for chunk_id, raw in zip(chunk_ids.tolist(), chunks, strict=True):
            expected = self.stable_chunk_id(document_id, int(raw["ordinal"]))
            if int(chunk_id) != expected:
                raise ValueError(f"知识库稳定 ID 校验失败: {path.name}")
            result[int(chunk_id)] = KnowledgeChunk(
                chunk_id=int(chunk_id),
                document_id=document_id,
                ordinal=int(raw["ordinal"]),
                title=str(payload["title"]),
                content=str(raw["content"]),
                category=str(payload.get("category") or "其他"),
                source_url=payload.get("source_url"),
                published_at=published_at,
                heading_path=raw.get("heading_path"),
                page_number=raw.get("page_number"),
                token_count=int(raw.get("token_count") or 0),
            )
        return result, chunk_ids, vectors, str(payload["embedding_model"])

    def _load_artifact_records(
        self, path: Path
    ) -> tuple[dict[int, KnowledgeChunk], str, int]:
        """Read searchable text and IDs without decompressing stored embeddings."""
        with np.load(path, allow_pickle=False) as archive:
            chunk_ids = np.asarray(archive["chunk_ids"], dtype=np.int64)
            payload = json.loads(archive["payload"].tobytes().decode("utf-8"))
        chunks = payload.get("chunks", [])
        if payload.get("schema_version") != KNOWLEDGE_SCHEMA_VERSION:
            raise ValueError(f"unsupported knowledge artifact format: {path.name}")
        if len(chunks) != len(chunk_ids):
            raise ValueError(f"knowledge artifact has inconsistent chunk data: {path.name}")

        published = payload.get("published_at")
        published_at = date.fromisoformat(published) if published else None
        document_id = int(payload["document_id"])
        records: dict[int, KnowledgeChunk] = {}
        for chunk_id, raw in zip(chunk_ids.tolist(), chunks, strict=True):
            expected = self.stable_chunk_id(document_id, int(raw["ordinal"]))
            if int(chunk_id) != expected:
                raise ValueError(f"stable chunk ID validation failed: {path.name}")
            records[int(chunk_id)] = KnowledgeChunk(
                chunk_id=int(chunk_id),
                document_id=document_id,
                ordinal=int(raw["ordinal"]),
                title=str(payload["title"]),
                content=str(raw["content"]),
                category=str(payload.get("category") or "其他"),
                source_url=payload.get("source_url"),
                published_at=published_at,
                heading_path=raw.get("heading_path"),
                page_number=raw.get("page_number"),
                token_count=int(raw.get("token_count") or 0),
            )
        return records, str(payload["embedding_model"]), int(payload["dimension"])

    def records(self, chunk_ids: list[int]) -> dict[int, KnowledgeChunk]:
        snapshot = self.snapshot()
        return {
            chunk_id: snapshot.records[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in snapshot.records
        }

    def _persist_empty(self) -> None:
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        target = settings.index_dir / "faiss.index"
        if target.exists():
            target.unlink()
        self._persist_manifest({"schema_version": KNOWLEDGE_SCHEMA_VERSION, "count": 0})

    def _persist(self, index: faiss.Index, count: int, dimension: int, model: str) -> None:
        settings.index_dir.mkdir(parents=True, exist_ok=True)
        target = settings.index_dir / "faiss.index"
        temp = Path(f"{target}.tmp")
        faiss.write_index(index, str(temp))
        os.replace(temp, target)
        self._persist_manifest(
            {
                "schema_version": KNOWLEDGE_SCHEMA_VERSION,
                "count": count,
                "dimension": dimension,
                "embedding_model": model,
                "document_count": len(list(settings.knowledge_artifact_dir.glob("*.npz"))),
            }
        )

    def _persist_manifest(self, metadata: dict[str, object]) -> None:
        target = settings.index_dir / "manifest.json"
        temp = Path(f"{target}.tmp")
        temp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)

    def dense_search(self, vector: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        snapshot = self.snapshot()
        if snapshot.dense is None or snapshot.count == 0:
            return []
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != snapshot.dense.d:
            raise ValueError("查询向量维度与知识库不一致")
        scores, ids = snapshot.dense.search(query, min(top_k, snapshot.count))
        return [
            (int(chunk_id), float(score))
            for chunk_id, score in zip(ids[0], scores[0], strict=False)
            if chunk_id >= 0
        ]

    def sparse_search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        snapshot = self.snapshot()
        if snapshot.bm25 is None or snapshot.count == 0:
            return []
        scores = np.asarray(snapshot.bm25.get_scores(tokenize(query)), dtype=np.float32)
        if not np.any(scores > 0):
            return []
        indexes = np.argsort(scores)[::-1][: min(top_k, len(scores))]
        return [
            (snapshot.chunk_ids[int(index)], float(scores[int(index)]))
            for index in indexes
            if scores[int(index)] > 0
        ]


index_manager = IndexManager()
