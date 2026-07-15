from __future__ import annotations

import threading
from typing import Protocol

import numpy as np

from app.core.config import settings


class Embedder(Protocol):
    dimension: int

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class BGEEmbedder:
    dimension = settings.embedding_dimension

    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()

    def _load(self):  # type: ignore[no-untyped-def]
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(
                        settings.embedding_model,
                        device=None if settings.model_device == "auto" else settings.model_device,
                        local_files_only=settings.model_local_files_only,
                    )
        return self._model

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._load().encode(
            texts,
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        result = np.asarray(vectors, dtype=np.float32)
        if result.ndim == 1:
            result = result.reshape(1, -1)
        self.dimension = int(result.shape[1])
        return result

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts)

    def embed_query(self, text: str) -> np.ndarray:
        instruction = "为这个句子生成表示以用于检索相关文章："
        return self._encode([instruction + text])[0]


embedder: Embedder = BGEEmbedder()
