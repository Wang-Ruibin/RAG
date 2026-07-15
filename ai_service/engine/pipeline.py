"""
RAG pipeline — orchestrates the full retrieval-augmented generation workflow.

Connects Retriever → Prompts → Generator in a single callable interface,
with both synchronous and streaming modes, plus full indexing utilities.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Generator as GeneratorType

from . import chunker, embedding, loader, prompts
from .generator import Generator
from .retriever import Retriever
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """End-to-end RAG pipeline that orchestrates retrieval, prompt assembly,
    and LLM generation.

    Parameters
    ----------
    retriever : Retriever, optional
        Pre-configured retriever instance.  Created automatically from
        *vector_store* when omitted.
    generator : Generator, optional
        Pre-configured LLM generator instance.  Created automatically
        when omitted.
    vector_store : VectorStore, optional
        Pre-configured vector store instance.  When omitted a new one is
        created, which auto-loads persisted index files from disk if they
        exist.
    """

    def __init__(
        self,
        retriever: Retriever | None = None,
        generator: Generator | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.vector_store = vector_store or VectorStore()
        self.retriever = retriever or Retriever(vector_store=self.vector_store)
        self.generator = generator or Generator()
        logger.info("RAGPipeline initialised")

    # ------------------------------------------------------------------
    # Sync pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Run the full RAG pipeline synchronously.

        Parameters
        ----------
        query : str
            The user's question.
        top_k : int
            Number of chunks to retrieve (default 5).
        min_score : float
            Minimum similarity score threshold (default 0.0).
        temperature : float
            LLM sampling temperature (default 0.3).
        max_tokens : int
            Maximum tokens in the generated response (default 1024).

        Returns
        -------
        dict
            ``{"answer": str, "sources": list[dict]}``.
            When no relevant documents are found the *answer* will be
            ``"未找到相关校园信息"`` and *sources* an empty list.
        """
        # 1. Retrieve
        chunks = self.retriever.retrieve(query, top_k, min_score)

        # 2. Graceful fallback when no results
        if not chunks:
            logger.info("No relevant chunks found for query: %s", query[:60])
            return {"answer": "未找到相关校园信息", "sources": []}

        # 3. Build prompt pair from retrieved chunks
        system_prompt, user_prompt = prompts.build_prompt(query, chunks)

        # 4. Generate answer
        answer = self.generator.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 5. Structure output with source metadata
        return prompts.format_answer(answer, chunks)

    # ------------------------------------------------------------------
    # Streaming pipeline
    # ------------------------------------------------------------------

    def run_stream(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> GeneratorType[dict[str, Any], None, None]:
        """Run the RAG pipeline with streaming token output.

        Yields intermediate event dicts so callers can display progress
        indicators, show retrieved sources, and stream the answer token
        by token to the user.

        Parameters
        ----------
        query : str
            The user's question.
        top_k : int
            Number of chunks to retrieve (default 5).
        min_score : float
            Minimum similarity score threshold (default 0.0).
        temperature : float
            LLM sampling temperature (default 0.3).
        max_tokens : int
            Maximum tokens in the generated response (default 1024).

        Yields
        ------
        dict
            Event dicts with a ``"type"`` discriminator:

            - ``{"type": "status", "message": "检索中..."}``
            - ``{"type": "sources", "data": [...]}``
            - ``{"type": "token", "content": "..."}``
            - ``{"type": "done", "answer": "...", "sources": [...]}``
        """
        # 1. Status — retrieval phase
        yield {"type": "status", "message": "检索中..."}

        # 2. Retrieve
        chunks = self.retriever.retrieve(query, top_k, min_score)

        # 3. No results — short-circuit with fallback
        if not chunks:
            yield {
                "type": "done",
                "answer": "未找到相关校园信息",
                "sources": [],
            }
            return

        # 4. Emit sources for frontend display
        sources = [
            {
                "title": c.get("title", ""),
                "content_preview": c.get("content", "")[:100],
                "score": c.get("score", 0.0),
            }
            for c in chunks
        ]
        yield {"type": "sources", "data": sources}

        # 5. Build prompt
        system_prompt, user_prompt = prompts.build_prompt(query, chunks)

        # 6. Stream tokens from the LLM
        answer_parts: list[str] = []
        for token in self.generator.generate_stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            answer_parts.append(token)
            yield {"type": "token", "content": token}

        # 7. Signal completion with full answer + sources
        full_answer = "".join(answer_parts)
        yield {"type": "done", "answer": full_answer, "sources": sources}

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_documents(
        self,
        docs_dir: str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> dict[str, Any]:
        """Load, chunk, embed, and index all knowledge documents.

        This is a full indexing pipeline that replaces any existing index
        in the vector store.  When *docs_dir* is ``None`` the default
        ``knowledge_docs/`` directory (relative to the project root) is
        used.

        Parameters
        ----------
        docs_dir : str, optional
            Path to the directory containing knowledge documents
            (``.md`` / ``.txt`` files).  Defaults to the project-level
            ``knowledge_docs/`` folder.
        chunk_size : int
            Maximum number of characters per chunk (default 500).
        chunk_overlap : int
            Overlap between consecutive chunks (default 50).

        Returns
        -------
        dict
            ``{"docs_count", "chunks_count", "indexed_count",
            "time_seconds"}``.
        """
        t0 = time.time()

        # 1. Load documents from disk
        docs = loader.load_knowledge_docs(docs_dir)
        doc_count = len(docs)
        logger.info("Loaded %d document(s)", doc_count)

        if doc_count == 0:
            elapsed = time.time() - t0
            logger.warning("No documents found to index")
            return {
                "docs_count": 0,
                "chunks_count": 0,
                "indexed_count": 0,
                "time_seconds": round(elapsed, 2),
            }

        # 2. Split into overlapping chunks
        chunks = chunker.chunk_docs(docs, chunk_size, chunk_overlap)
        chunk_count = len(chunks)
        logger.info("Created %d chunk(s)", chunk_count)

        # 3. Embed all chunk texts in a single batch
        texts = [c["content"] for c in chunks]
        vectors = embedding.embed(texts)

        # 4. Build parallel metadata list
        metadata = [
            {
                "content": c["content"],
                "doc_id": c["doc_id"],
                "chunk_index": c["chunk_index"],
                "title": c["title"],
                "category": c["category"],
                "source_url": c["source_url"],
            }
            for c in chunks
        ]

        # 5. Build / replace the FAISS index and persist
        self.vector_store.build(vectors, metadata)
        self.vector_store.save()

        elapsed = time.time() - t0
        logger.info("Indexed %d chunks in %.2fs", chunk_count, elapsed)

        return {
            "docs_count": doc_count,
            "chunks_count": chunk_count,
            "indexed_count": chunk_count,
            "time_seconds": round(elapsed, 2),
        }

    def add_document(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> dict[str, Any]:
        """Add a single document to the existing vector store.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the document (``.md`` or ``.txt``).
        chunk_size : int
            Maximum number of characters per chunk (default 500).
        chunk_overlap : int
            Overlap between consecutive chunks (default 50).

        Returns
        -------
        dict
            ``{"chunks_count", "indexed", "doc_id"}``.
        """
        # 1. Load the single document
        doc = loader.load_file(file_path)
        doc_id = doc["doc_id"]

        # 2. Chunk
        chunks = chunker.chunk_docs([doc], chunk_size, chunk_overlap)
        chunk_count = len(chunks)
        logger.info("Created %d chunk(s) for %s", chunk_count, file_path)

        if chunk_count == 0:
            return {"chunks_count": 0, "indexed": 0, "doc_id": doc_id}

        # 3. Embed
        texts = [c["content"] for c in chunks]
        vectors = embedding.embed(texts)

        # 4. Metadata
        metadata = [
            {
                "content": c["content"],
                "doc_id": c["doc_id"],
                "chunk_index": c["chunk_index"],
                "title": c["title"],
                "category": c["category"],
                "source_url": c["source_url"],
            }
            for c in chunks
        ]

        # 5. Incrementally add to the existing index and persist
        self.vector_store.add(vectors, metadata)
        self.vector_store.save()

        logger.info("Added %d chunk(s) (doc_id=%s)", chunk_count, doc_id)
        return {
            "chunks_count": chunk_count,
            "indexed": chunk_count,
            "doc_id": doc_id,
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return combined pipeline and vector store statistics.

        Returns
        -------
        dict
            Top-level keys ``"pipeline"`` and ``"vector_store"``.
        """
        store_stats = self.vector_store.get_stats()
        return {
            "pipeline": {
                "retriever_ready": self.vector_store.index is not None,
                "default_top_k": 5,
                "default_min_score": 0.0,
            },
            "vector_store": store_stats,
        }
