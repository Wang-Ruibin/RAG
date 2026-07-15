"""
Retriever for the RAG engine.

Wraps the VectorStore with query-embedding logic and scoring thresholds.
"""

from typing import Optional

import numpy as np

from .embedding import embed, embed_query
from .vector_store import VectorStore


class Retriever:
    """Simple Top-K retriever backed by a VectorStore.

    Parameters
    ----------
    vector_store : VectorStore, optional
        An existing VectorStore instance. If ``None``, a new one is created
        (which auto-loads from disk if persisted files exist).
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self._vector_store = vector_store or VectorStore()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[dict]:
        """Embed *query* and return the top-*k* most similar documents.

        Parameters
        ----------
        query : str
            The query string.
        top_k : int
            Number of nearest neighbours to return (default 5).
        min_score : float
            Minimum similarity score threshold (default 0.0).
            Results with ``score <= min_score`` are excluded.

        Returns
        -------
        list[dict]
            Each result contains *content*, *doc_id*, *title*, *category*,
            *source_url*, *score*, and *chunk_index*.

        Raises
        ------
        RuntimeError
            If the underlying VectorStore has not been built.
        """
        if not query or not query.strip():
            return []

        self._ensure_built()

        query_vec = embed_query(query)                     # (1, dim)
        results = self._vector_store.search(query_vec, top_k)

        if min_score > 0.0:
            results = [r for r in results if r["score"] > min_score]

        return results

    def batch_retrieve(
        self,
        queries: list[str],
        top_k: int = 5,
    ) -> list[list[dict]]:
        """Retrieve results for multiple queries at once.

        All valid (non-empty) queries are embedded in a single batch call
        for efficiency.  Empty queries produce an empty result list.

        Parameters
        ----------
        queries : list[str]
            List of query strings.
        top_k : int
            Number of results per query (default 5).

        Returns
        -------
        list[list[dict]]
            Outer list corresponds to each query; inner lists contain result
            dicts.

        Raises
        ------
        RuntimeError
            If the underlying VectorStore has not been built.
        """
        if not queries:
            return []

        self._ensure_built()

        # Separate valid queries from blank ones while tracking positions
        valid_indices: list[int] = []
        valid_texts: list[str] = []
        for i, q in enumerate(queries):
            if q and q.strip():
                valid_indices.append(i)
                valid_texts.append(q)

        if not valid_texts:
            return [[] for _ in queries]

        # Batch embed all valid queries at once
        query_vectors = embed(valid_texts)  # (n_valid, dim)

        # Search each query vector
        result_lists: list[list[dict]] = [[] for _ in queries]
        for pos, idx in enumerate(valid_indices):
            q_vec = query_vectors[pos : pos + 1]  # keep 2-D
            result_lists[idx] = self._vector_store.search(q_vec, top_k)

        return result_lists

    def get_params(self) -> dict:
        """Return default retrieval parameters.

        Returns
        -------
        dict
            Keys: *top_k*, *min_score*.
        """
        return {
            "top_k": 5,
            "min_score": 0.0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_built(self) -> None:
        """Check that the underlying index is available, raising otherwise."""
        if self._vector_store.index is None:
            raise RuntimeError(
                "VectorStore has not been built. "
                "Call vector_store.build(vectors, metadata) or "
                "ensure the persisted index exists on disk."
            )
