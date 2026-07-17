from __future__ import annotations

import json
import os
import threading
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings

QA_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class QaMatch:
    entry_id: int
    title: str
    question: str
    answer: str
    score: float


@dataclass(frozen=True, slots=True)
class QaSnapshot:
    dense: faiss.IndexIDMap2 | None
    records: dict[int, QaMatch]


class QaIndexManager:
    """Small hidden vector index for approved QA pairs.

    SQL stores only entry metadata and provenance edges. Question text, answer
    text, and embeddings live in per-entry NPZ artifacts.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot = QaSnapshot(None, {})

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._snapshot.records)

    def artifact_path(self, entry_id: int) -> Path:
        return settings.qa_artifact_dir / f"{entry_id}.npz"

    def load(self, valid_entry_ids: Collection[int] | None = None) -> int:
        with self._lock:
            settings.ensure_directories()
            if valid_entry_ids is not None:
                valid = {int(value) for value in valid_entry_ids}
                for artifact in settings.qa_artifact_dir.glob("*.npz"):
                    try:
                        entry_id = int(artifact.stem)
                    except ValueError:
                        continue
                    if entry_id not in valid:
                        artifact.unlink()
            self._rebuild_unlocked()
            return len(self._snapshot.records)

    def upsert(
        self,
        *,
        entry_id: int,
        title: str,
        question: str,
        answer: str,
        vector: np.ndarray,
    ) -> None:
        matrix = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if not np.all(np.isfinite(matrix)):
            raise ValueError("QA Embedding 包含非有限数值")
        payload = json.dumps(
            {
                "schema_version": QA_SCHEMA_VERSION,
                "entry_id": entry_id,
                "title": title,
                "question": question,
                "answer": answer,
                "embedding_model": settings.embedding_model,
                "dimension": int(matrix.shape[1]),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        target = self.artifact_path(entry_id)
        temp = Path(f"{target}.tmp")
        with self._lock:
            settings.ensure_directories()
            with temp.open("wb") as handle:
                np.savez_compressed(
                    handle,
                    embedding=matrix,
                    payload=np.frombuffer(payload, dtype=np.uint8),
                )
            os.replace(temp, target)
            self._rebuild_unlocked()

    def delete(self, entry_id: int) -> bool:
        with self._lock:
            target = self.artifact_path(entry_id)
            existed = target.exists()
            if existed:
                target.unlink()
            self._rebuild_unlocked()
            return existed

    def get(self, entry_id: int) -> QaMatch | None:
        with self._lock:
            return self._snapshot.records.get(entry_id)

    def search(self, vector: np.ndarray, top_k: int | None = None) -> list[QaMatch]:
        with self._lock:
            snapshot = self._snapshot
            if snapshot.dense is None or not snapshot.records:
                return []
            query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
            if query.shape[1] != snapshot.dense.d:
                return []
            limit = min(max(1, top_k or settings.qa_retrieval_top_k), len(snapshot.records))
            scores, ids = snapshot.dense.search(query, limit)
            matches: list[QaMatch] = []
            for score, entry_id in zip(scores[0], ids[0], strict=False):
                record = snapshot.records.get(int(entry_id))
                if record is None:
                    continue
                matches.append(
                    QaMatch(
                        entry_id=record.entry_id,
                        title=record.title,
                        question=record.question,
                        answer=record.answer,
                        score=float(score),
                    )
                )
            return matches

    def _rebuild_unlocked(self) -> None:
        records: dict[int, QaMatch] = {}
        vectors: list[np.ndarray] = []
        ids: list[int] = []
        dimension: int | None = None
        for artifact in sorted(settings.qa_artifact_dir.glob("*.npz")):
            try:
                with np.load(artifact, allow_pickle=False) as archive:
                    vector = np.asarray(archive["embedding"], dtype=np.float32).reshape(1, -1)
                    payload = json.loads(archive["payload"].tobytes().decode("utf-8"))
                if payload.get("schema_version") != QA_SCHEMA_VERSION:
                    continue
                entry_id = int(payload["entry_id"])
                current_dimension = int(vector.shape[1])
                if dimension is None:
                    dimension = current_dimension
                if current_dimension != dimension:
                    continue
                records[entry_id] = QaMatch(
                    entry_id=entry_id,
                    title=str(payload.get("title") or "问答知识"),
                    question=str(payload.get("question") or ""),
                    answer=str(payload.get("answer") or ""),
                    score=1.0,
                )
                vectors.append(vector[0])
                ids.append(entry_id)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
        if not vectors or dimension is None:
            self._snapshot = QaSnapshot(None, {})
            return
        dense = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))
        dense.add_with_ids(np.asarray(vectors, dtype=np.float32), np.asarray(ids, dtype=np.int64))
        self._snapshot = QaSnapshot(dense, records)


qa_index_manager = QaIndexManager()
