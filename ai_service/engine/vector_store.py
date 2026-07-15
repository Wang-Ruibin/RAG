"""
FAISS vector store for the RAG engine.

Provides a persistent vector index with inner-product similarity search,
metadata aligned by index position, and full CRUD lifecycle.
"""

import json
import os

import faiss
import numpy as np


class VectorStore:
    """Persistent vector index backed by FAISS (IndexFlatIP) with JSON metadata.

    Parameters
    ----------
    index_path : str
        Path to the FAISS index file, relative to ``ai_service/``.
    meta_path : str
        Path to the metadata JSON file, relative to ``ai_service/``.

    If both files already exist on construction they are loaded automatically.
    """

    def __init__(self, index_path: str = "data/faiss.index", meta_path: str = "data/metadata.json"):
        # Resolve paths relative to the ai_service/ directory (one level up from engine/)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.index_path = os.path.join(base_dir, index_path)
        self.meta_path = os.path.join(base_dir, meta_path)

        self.index: faiss.Index | None = None
        self.vectors: np.ndarray | None = None
        self.metadata: list[dict] = []

        # Auto-load if persisted files exist
        self.load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, vectors: np.ndarray, metadata: list[dict]) -> None:
        """Create a new index from scratch.

        Parameters
        ----------
        vectors : np.ndarray
            Shape ``(n_vectors, dim)``.
        metadata : list[dict]
            Parallel list of metadata dicts, one per vector.
        """
        self.vectors = vectors.copy()
        self.metadata = list(metadata)
        dim = int(vectors.shape[1])
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(vectors)
        n = vectors.shape[0]
        print(f"Built index with {n} vectors, dim={dim}")

    def add(self, vectors: np.ndarray, metadata: list[dict]) -> None:
        """Add vectors to an existing index, or build a new one if none exists.

        Parameters
        ----------
        vectors : np.ndarray
            Shape ``(n_vectors, dim)``.
        metadata : list[dict]
            Parallel list of metadata dicts, one per vector.
        """
        if self.index is None:
            self.build(vectors, metadata)
            return

        self.index.add(vectors)
        if self.vectors is None:
            self.vectors = vectors.copy()
        else:
            self.vectors = np.concatenate([self.vectors, vectors], axis=0)
        self.metadata.extend(metadata)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        """Search the index for the *top_k* most similar vectors.

        Parameters
        ----------
        query_vector : np.ndarray
            1-D or 2-D array.  When 1-D it is reshaped to ``(1, dim)``.
        top_k : int
            Number of nearest neighbours to return (default 5).

        Returns
        -------
        list[dict]
            Each result contains *content*, *doc_id*, *title*, *category*,
            *source_url*, *score*, and *chunk_index*.  Results with
            ``score < 0`` are excluded.
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Ensure 2-D input
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        distances, indices = self.index.search(query_vector, top_k)

        results: list[dict] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue  # FAISS sentinel for "not enough results"
            score = float(dist)
            if score < 0:
                continue  # Not similar at all

            meta = self.metadata[idx]
            results.append({
                "content": meta.get("content", ""),
                "doc_id": meta.get("doc_id", ""),
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "source_url": meta.get("source_url", ""),
                "score": score,
                "chunk_index": meta.get("chunk_index", 0),
            })

        return results

    def delete(self, doc_id: str) -> int:
        """Remove all vectors belonging to *doc_id* and rebuild the index.

        Parameters
        ----------
        doc_id : str
            Document identifier to remove.

        Returns
        -------
        int
            Number of deleted entries.
        """
        if self.index is None or not self.metadata:
            return 0

        keep_indices: list[int] = []
        keep_metadata: list[dict] = []
        deleted_count = 0

        for i, meta in enumerate(self.metadata):
            if meta.get("doc_id") == doc_id:
                deleted_count += 1
            else:
                keep_indices.append(i)
                keep_metadata.append(meta)

        if deleted_count == 0:
            return 0

        # Filter vectors
        self.vectors = self.vectors[keep_indices]
        self.metadata = keep_metadata

        # Rebuild the FAISS index from scratch
        if len(self.vectors) > 0:
            dim = self.vectors.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(self.vectors)
        else:
            self.index = None
            self.vectors = None

        return deleted_count

    def save(self) -> None:
        """Persist the index and metadata to disk."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """Load index and metadata from disk.

        Returns
        -------
        bool
            ``True`` if both files existed and were loaded, ``False`` otherwise.
        """
        index_exists = os.path.isfile(self.index_path)
        meta_exists = os.path.isfile(self.meta_path)

        if not (index_exists and meta_exists):
            return False

        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        # Reconstruct in-memory vectors from the FAISS index
        n = self.index.ntotal
        if n > 0:
            self.vectors = self.index.reconstruct_n(0, n)
        else:
            self.vectors = None

        return True

    def get_stats(self) -> dict:
        """Return summary statistics about the store.

        Returns
        -------
        dict
            Keys: *total_vectors*, *dimension*, *index_type*, *metadata_file_size*.
        """
        stats: dict = {
            "total_vectors": 0,
            "dimension": 0,
            "index_type": "None",
            "metadata_file_size": 0,
        }
        if self.index is not None:
            stats["total_vectors"] = self.index.ntotal
            stats["dimension"] = self.index.d
            stats["index_type"] = type(self.index).__name__
        if os.path.isfile(self.meta_path):
            stats["metadata_file_size"] = os.path.getsize(self.meta_path)
        return stats
