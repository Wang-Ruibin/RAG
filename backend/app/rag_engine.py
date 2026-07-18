"""RAG engine service for the campus QA system.

Wraps sentence-transformers + FAISS into a singleton service class
that can be used by the FastAPI backend for document ingestion,
semantic search, and SSE-streamed answer generation.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterator, Optional
import hashlib
import json
import threading
import time

import numpy as np

from .config import settings

# OpenAI-compatible client (DeepSeek, DashScope, etc.)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Lazy optional dependencies (graceful degradation when packages missing)
# ---------------------------------------------------------------------------

_HAS_PYPDF = False
_HAS_DOCX = False

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    pypdf = None  # type: ignore[assignment]

try:
    import docx
    _HAS_DOCX = True
except ImportError:
    docx = None  # type: ignore[assignment]


# ===================================================================
# ChineseRecursiveTextSplitter
# ===================================================================


class ChineseRecursiveTextSplitter:
    """Chinese-aware recursive text splitter.

    Splitting priority (coarse → fine):
       paragraph (\\n\\n) → line (\\n) → Chinese period (。！？)
       → semicolon (；) → comma (，) → enumeration comma (、)
       → character fallback

    Guarantees every chunk ≤ *chunk_size* characters while keeping
    semantic boundaries where possible.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        if chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if chunk_overlap < 0:
            chunk_overlap = 0
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 3

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Chinese-priority separator chain (last = empty string = char split)
        self.separators: list[str] = [
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            "；",
            "，",
            "、",
            "",
        ]

    # ------------------------------------------------------------------
    def split_text(self, text: str) -> list[str]:
        """Return a list of text chunks not exceeding *chunk_size*."""
        if not text or not text.strip():
            return []
        raw = self._recursive_split(text, self.separators, self.chunk_size)
        merged = self._merge_small_chunks(raw)
        return merged if merged else raw

    # ------------------------------------------------------------------
    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
    ) -> list[str]:
        """Recursively split *text* trying each separator in order."""
        if len(text) <= chunk_size:
            return [text]

        if not separators:
            # fallback: character-level split with overlap
            step = chunk_size - self.chunk_overlap
            step = max(step, 1)
            return [
                text[i: i + chunk_size]
                for i in range(0, len(text), step)
            ]

        sep = separators[0]
        rest = separators[1:]

        parts: list[str] = []

        if sep in ("。", "！", "？", "；"):
            # sentence-ending punctuation: keep the separator on the left
            _split = text.split(sep)
            for i, part in enumerate(_split):
                if not part:
                    continue
                if i < len(_split) - 1:
                    parts.append(part + sep)
                else:
                    parts.append(part)
        elif sep == "":
            parts = list(text)
        else:
            _split = text.split(sep)
            parts = [p for p in _split if p]

        if len(parts) <= 1:
            return self._recursive_split(text, rest, chunk_size)

        result: list[str] = []
        for part in parts:
            if len(part) <= chunk_size:
                result.append(part)
            else:
                result.extend(self._recursive_split(part, rest, chunk_size))
        return result

    # ------------------------------------------------------------------
    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        """Merge adjacent small chunks up to *chunk_size*."""
        merged: list[str] = []
        buf = ""

        for c in chunks:
            c = c.strip()
            if not c:
                continue
            if not buf:
                buf = c
            elif len(buf) + len(c) <= self.chunk_size:
                buf += c
            else:
                merged.append(buf)
                buf = c

        if buf:
            merged.append(buf)
        return merged


# ===================================================================
# HHURAGEngine
# ===================================================================


class HHURAGEngine:
    """Singleton RAG engine for the campus QA system.

    Uses *sentence-transformers* for embeddings and *FAISS* (IndexFlatIP)
    for vector similarity search — fully local, no external API calls.
    """

    _instance: Optional["HHURAGEngine"] = None
    _initialized: bool = False
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls, *args: Any, **kwargs: Any) -> "HHURAGEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # __init__
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        if self._initialized:
            return

        # --- LLM client (lazy-loaded) ---
        self._llm_client: Optional["OpenAI"] = None

        # --- embedding model (lazy-loaded) ---
        self._model: Optional[SentenceTransformer] = None
        self._model_name: str = settings.embedding_model

        # --- FAISS index ---
        self._index: Optional[faiss.Index] = None
        self._index_dim: int = 384  # paraphrase-multilingual-MiniLM-L12-v2

        # --- chunk store ---
        self._chunks: list[dict[str, Any]] = []
        self._index_lock = threading.RLock()

        # --- persistence ---
        # FAISS C++ does not support paths with CJK characters on Windows.
        # Use system TEMP as fallback when the project path contains non-ASCII.
        _project_data_dir = Path(settings.data_dir) / "rag_index"
        try:
            _project_data_dir.mkdir(parents=True, exist_ok=True)
            # Test FAISS can write to this path
            if not all(c < 128 for c in str(_project_data_dir).encode("utf-8")):
                raise OSError("Non-ASCII path detected")
            self._persist_dir = _project_data_dir
        except (OSError, UnicodeEncodeError):
            # Fallback to ASCII-only temp path
            import tempfile
            self._persist_dir = Path(tempfile.gettempdir()) / "hhu-rag-index"
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            print(f"[RAG] Using ASCII fallback persist dir: {self._persist_dir}")

        # --- splitter ---
        self._splitter = ChineseRecursiveTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        # attempt to restore cached index
        self._load_cache()

        self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self) -> SentenceTransformer:
        """Load (and cache) the sentence-transformers embedding model."""
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _ensure_index(self, dimension: int = 384) -> faiss.Index:
        """Return the existing FAISS index, or create a new IndexFlatIP."""
        if self._index is None:
            if faiss is None:
                raise ImportError(
                    "faiss is not installed. Run: pip install faiss-cpu"
                )
            self._index = faiss.IndexFlatIP(dimension)
            self._index_dim = dimension
        return self._index

    # ------------------------------------------------------------------
    # Cache persistence
    # ------------------------------------------------------------------

    def _cache_index_path(self) -> Path:
        return self._persist_dir / "faiss_index.bin"

    def _cache_chunks_path(self) -> Path:
        return self._persist_dir / "chunks.json"

    def _save_cache(self) -> None:
        """Write FAISS index + chunks to the persist directory.

        Failures are logged but NOT propagated — the in-memory index
        continues to work for queries even if disk persistence fails.
        """
        idx_path = self._cache_index_path()
        ch_path = self._cache_chunks_path()

        with self._index_lock:
            try:
                self._persist_dir.mkdir(parents=True, exist_ok=True)

                if self._index is not None and self._index.ntotal > 0:
                    faiss.write_index(self._index, str(idx_path))
                else:
                    if idx_path.exists():
                        idx_path.unlink()

                with open(ch_path, "w", encoding="utf-8") as f:
                    json.dump(self._chunks, f, ensure_ascii=False, indent=2)
            except Exception as exc:
                print(
                    f"[RAG] Cache write failed (in-memory index unaffected): {exc}"
                )

    def _load_cache(self) -> None:
        """Restore FAISS index + chunks from the persist directory.

        Returns (index, chunks); both are ``None`` on failure.
        """
        idx_path = self._cache_index_path()
        ch_path = self._cache_chunks_path()

        if not idx_path.exists() or not ch_path.exists():
            return

        try:
            with self._index_lock:
                self._index = faiss.read_index(str(idx_path))
                with open(ch_path, "r", encoding="utf-8") as f:
                    self._chunks = json.load(f)
        except Exception:
            # corrupt cache — start fresh
            self._index = None
            self._chunks = []

    # ------------------------------------------------------------------
    # File parsing
    # ------------------------------------------------------------------

    def _read_file(self, file_path: Path) -> str:
        """Read text content from **file_path** supporting .md, .txt, .pdf,
        .docx."""
        ext = file_path.suffix.lower()

        if ext in (".md", ".txt"):
            return file_path.read_text(encoding="utf-8")

        if ext == ".pdf":
            if not _HAS_PYPDF:
                raise ImportError(
                    "pypdf is required to read PDF files. "
                    "Run: pip install pypdf"
                )
            text_parts: list[str] = []
            with open(file_path, "rb") as fh:
                reader = pypdf.PdfReader(fh)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
            return "\n".join(text_parts)

        if ext == ".docx":
            if not _HAS_DOCX:
                raise ImportError(
                    "python-docx is required to read .docx files. "
                    "Run: pip install python-docx"
                )
            doc = docx.Document(str(file_path))
            return "\n".join(p.text or "" for p in doc.paragraphs)

        raise ValueError(f"Unsupported file type: {ext}")

    # ------------------------------------------------------------------
    # add_document
    # ------------------------------------------------------------------

    def add_document(
        self,
        file_path: Path | str,
        document_id: int,
        title: str = "",
        category: str = "其他",
        db=None,  # optional database connection for status update
        source: str | None = None,  # optional source override (e.g. "subdir/file.md")
    ) -> int:
        """Ingest a single document into the RAG index.

        Parameters
        ----------
        file_path : Path | str
            Path to the document file (.md, .txt, .pdf, .docx).
        document_id : int
            Primary key of the ``documents`` table row.
        title : str
            Human-readable document title.
        category : str
            Document category (e.g. '招生', '教务', '校园生活').
        db : sqlite3.Connection or None
            If provided, the ``documents`` table status / chunk_count
            will be updated after ingestion.

        Returns
        -------
        int
            Number of chunks generated.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 1. read
        try:
            text = self._read_file(file_path)
        except Exception as exc:
            if db is not None:
                db.execute(
                    """UPDATE documents SET status='ERROR', error=?
                       WHERE id=?""",
                    (str(exc), document_id),
                )
                db.commit()
            raise

        if not text.strip():
            if db is not None:
                db.execute(
                    """UPDATE documents SET status='ERROR', error=?
                       WHERE id=?""",
                    ("Empty file content", document_id),
                )
                db.commit()
            return 0

        # 2. split
        raw_chunks = self._splitter.split_text(text)
        if not raw_chunks:
            if db is not None:
                db.execute(
                    """UPDATE documents SET status='ERROR', error=?
                       WHERE id=?""",
                    ("No chunks after splitting", document_id),
                )
                db.commit()
            return 0

        # 3. build chunk records
        new_chunks: list[dict[str, Any]] = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
            new_chunks.append({
                "text": chunk_text,
                "source": source if source is not None else file_path.name,
                "chunk_id": f"doc{document_id}#chunk{i:04d}",
                "document_id": document_id,
                "title": title,
                "metadata": {
                    "category": category,
                    "file_name": file_path.name,
                },
            })

        if not new_chunks:
            return 0

        with self._index_lock:
            # 4. generate embeddings
            model = self._get_model()
            texts = [c["text"] for c in new_chunks]
            embeddings = model.encode(
                texts, show_progress_bar=False, normalize_embeddings=True
            )

            # 5. add to FAISS
            index = self._ensure_index(dimension=embeddings.shape[1])
            index.add(embeddings.astype(np.float32))

            # 6. merge into chunk store
            self._chunks.extend(new_chunks)

            # 7. persist
            self._save_cache()

        # 8. update database if connection provided
        chunk_count = len(new_chunks)
        if db is not None:
            db.execute(
                """UPDATE documents
                   SET status='READY', chunk_count=?, updated_at=?
                   WHERE id=?""",
                (chunk_count, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 document_id),
            )
            db.commit()

        return chunk_count

    # ------------------------------------------------------------------
    # delete_document
    # ------------------------------------------------------------------

    def delete_document(self, document_id: int, persist: bool = True) -> int:
        """Remove all chunks belonging to **document_id** from the index.

        Returns the number of chunks removed.
        """
        with self._index_lock:
            before = len(self._chunks)
            self._chunks = [
                c for c in self._chunks
                if c.get("document_id") != document_id
            ]
            removed = before - len(self._chunks)

            if removed == 0:
                return 0

            # Rebuild FAISS index from remaining chunks
            if self._chunks:
                model = self._get_model()
                texts = [c["text"] for c in self._chunks]
                embeddings = model.encode(
                    texts, show_progress_bar=False, normalize_embeddings=True
                )
                dim = embeddings.shape[1]
                new_index = faiss.IndexFlatIP(dim)
                new_index.add(embeddings.astype(np.float32))
                self._index = new_index
                self._index_dim = dim
            else:
                self._index = None

            if persist:
                self._save_cache()

        return removed

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        conversation_id: int | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve relevant chunks and generate an answer.

        Parameters
        ----------
        question : str
            The user's question in Chinese or English.
        conversation_id : int or None
            Future use — conversation context tracking.
        top_k : int or None
            Number of chunks to retrieve (defaults to ``settings.top_k``).

        Returns
        -------
        dict
            ``{"answer": str, "sources": list[dict]}``
        """
        if top_k is None:
            top_k = settings.top_k

        retrieved = self._retrieve(question, top_k=top_k)
        answer = self.generate_answer(question, retrieved)

        sources = [
            {
                "chunk_id": r["chunk_id"],
                "text": r["text"][:300],
                "source": r.get("source", ""),
                "title": r.get("title", ""),
                "score": r.get("score", 0.0),
            }
            for r in retrieved
        ]

        return {"answer": answer, "sources": sources}

    # ------------------------------------------------------------------
    # stream_query  (SSE streaming)
    # ------------------------------------------------------------------

    def stream_query(
        self,
        question: str,
        conversation_id: int | None = None,
        top_k: int | None = None,
    ) -> Iterator[str]:
        """Stream query results as Server-Sent Events (SSE).

        Yields
        ------
        str
            ``event: meta\\ndata: {{"sources": [...]}}\\n\\n``
            then zero or more ``event: token\\ndata: {{"text": "…"}}\\n\\n``
            then ``event: done\\ndata: {{}}\\n\\n``
        """
        if top_k is None:
            top_k = settings.top_k

        retrieved = self._retrieve(question, top_k=top_k)

        sources = [
            {
                "chunk_id": r["chunk_id"],
                "text": r["text"][:300],
                "source": r.get("source", ""),
                "title": r.get("title", ""),
                "score": r.get("score", 0.0),
            }
            for r in retrieved
        ]

        # 1. meta event (sources + conversation_id injected by caller)
        yield f"event: meta\ndata: {json.dumps({'sources': sources}, ensure_ascii=False)}\n\n"

        # 2. token events — streamed token by token from LLM or fallback
        # json.dumps handles all JSON string escaping (including \n), so raw
        # tokens are safe to pass directly without manual backslash handling.
        for token in self.stream_generate_answer(question, retrieved):
            yield f"event: token\ndata: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"

        # 3. done
        yield "event: done\ndata: {}\n\n"

    # ------------------------------------------------------------------
    # _retrieve  (internal)
    # ------------------------------------------------------------------

    def _retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Encode *query* and search the FAISS index.

        Returns a list of chunk dicts sorted by descending similarity,
        each containing at least ``text``, ``source``, ``chunk_id``,
        ``document_id``, ``title``, ``score``.
        """
        with self._index_lock:
            if self._index is None or self._index.ntotal == 0 or not self._chunks:
                return []

            model = self._get_model()
            q_vec = model.encode([query], normalize_embeddings=True)
            k = min(top_k, self._index.ntotal)
            distances, indices = self._index.search(
                q_vec.astype(np.float32), k,
            )

            results: list[dict[str, Any]] = []
            for i, idx in enumerate(indices[0]):
                if idx < 0 or idx >= len(self._chunks):
                    continue
                chunk = dict(self._chunks[idx])  # shallow copy
                chunk["score"] = round(float(distances[0][i]), 4)
                results.append(chunk)

        return results

    # ------------------------------------------------------------------
    # LLM client (lazy)
    # ------------------------------------------------------------------

    def _get_llm_client(self) -> Optional["OpenAI"]:
        """Return an OpenAI-compatible client, or ``None`` if no API key is
        configured.

        Checks ``LLM_API_KEY`` first, then falls back to the legacy
        ``DASHSCOPE_API_KEY`` for backward compatibility.
        """
        if self._llm_client is not None:
            return self._llm_client

        api_key = settings.llm_api_key or settings.dashscope_api_key
        if not api_key or OpenAI is None:
            return None

        self._llm_client = OpenAI(
            api_key=api_key,
            base_url=settings.llm_base_url,
        )
        return self._llm_client

    # ------------------------------------------------------------------
    # generate_answer
    # ------------------------------------------------------------------

    def generate_answer(
        self,
        query: str,
        retrieved: list[dict[str, Any]],
    ) -> str:
        """Generate a clean, natural-language answer.

        Strategy
        --------
        1. If an LLM API key is configured, build a grounded prompt from the
           retrieved chunks and call the OpenAI-compatible API.
        2. Otherwise, fall back to concatenating retrieved chunks with
           deduplication (old behaviour).
        """
        if not retrieved:
            return "抱歉，在现有知识库中未找到相关信息"

        # --------------------------------------------------------------
        # Path A — LLM-powered answer
        # --------------------------------------------------------------
        client = self._get_llm_client()
        if client is not None:
            chunks_text = "\n\n---\n\n".join(r["text"] for r in retrieved)
            prompt = (
                "你是一个河海大学的校园问答助手。请基于以下参考信息，用中文回答用户的问题。\n"
                "\n"
                "参考信息：\n"
                "---\n"
                f"{chunks_text}\n"
                "---\n"
                "\n"
                "要求：\n"
                "- 只基于参考信息回答，不要编造信息\n"
                "- 回答简洁、自然、有条理\n"
                "- 不要输出「根据参考信息」「根据资料」这类话\n"
                "- 如果参考信息不足以回答问题，诚实地说明\n"
                "\n"
                f"用户问题：{query}"
            )
            try:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                )
                answer = response.choices[0].message.content.strip()
                return answer if answer else "抱歉，无法生成有效回答"
            except Exception as exc:
                # Log and fall through to the non-LLM path
                print(f"[RAG] LLM API call failed, falling back: {exc}")

        # --------------------------------------------------------------
        # Path B — Fallback: concatenate chunks
        # --------------------------------------------------------------
        return self._generate_answer_fallback(query, retrieved)

    # ------------------------------------------------------------------
    # stream_generate_answer  (token-by-token streaming)
    # ------------------------------------------------------------------

    def stream_generate_answer(
        self,
        query: str,
        retrieved: list[dict[str, Any]],
    ) -> Iterator[str]:
        """Generate answer tokens one by one via streaming LLM or fallback.

        Yields individual text tokens as they become available from the
        OpenAI-compatible streaming API, or falls back to character-level
        streaming from the concatenation-based answer builder.

        Strategy
        --------
        1. If an LLM API key is configured, create a ``stream=True``
           completion and yield each delta token as it arrives.
        2. Otherwise, compute the full fallback answer then yield its
           characters one at a time.
        """
        if not retrieved:
            yield "抱歉，在现有知识库中未找到相关信息"
            return

        # --------------------------------------------------------------
        # Path A — LLM-powered streaming
        # --------------------------------------------------------------
        client = self._get_llm_client()
        if client is not None:
            chunks_text = "\n\n---\n\n".join(r["text"] for r in retrieved)
            prompt = (
                "你是一个河海大学的校园问答助手。请基于以下参考信息，用中文回答用户的问题。\n"
                "\n"
                "参考信息：\n"
                "---\n"
                f"{chunks_text}\n"
                "---\n"
                "\n"
                "要求：\n"
                "- 只基于参考信息回答，不要编造信息\n"
                "- 回答简洁、自然、有条理\n"
                "- 不要输出「根据参考信息」「根据资料」这类话\n"
                "- 如果参考信息不足以回答问题，诚实地说明\n"
                "\n"
                f"用户问题：{query}"
            )
            try:
                stream = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    temperature=0.3,
                    max_tokens=2000,
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as exc:
                # Log and fall through to the non-LLM path
                print(f"[RAG] LLM streaming failed, falling back: {exc}")

        # --------------------------------------------------------------
        # Path B — Fallback: compute full answer then yield characters
        # --------------------------------------------------------------
        answer = self._generate_answer_fallback(query, retrieved)
        for char in answer:
            yield char

    # ------------------------------------------------------------------
    # _generate_answer_fallback  (non-LLM concatenation)
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_answer_fallback(
        query: str,
        retrieved: list[dict[str, Any]],
    ) -> str:
        """Assemble a coherent answer from retrieved text chunks by
        concatenation with deduplication (legacy behaviour).

        Strategy
        --------
        1. Group by source document.
        2. Within each group, sort by score descending.
        3. Deduplicate highly overlapping chunks (>80 % character overlap).
        4. Format as continuous paragraphs.
        """
        if not retrieved:
            return "抱歉，在现有知识库中未找到相关信息"

        # Group by source
        groups: dict[str, list[dict[str, Any]]] = OrderedDict()
        for r in retrieved:
            src = r.get("source", "unknown")
            groups.setdefault(src, []).append(r)

        # Select chunks with dedup
        selected: list[tuple[str, str, str]] = []
        seen_texts: list[str] = []

        for src, items in groups.items():
            items.sort(key=lambda x: x["score"], reverse=True)
            for item in items:
                t = item["text"].strip()
                if not t:
                    continue
                t_chars = set(t)
                duplicate = False
                for existing in seen_texts:
                    intersection = t_chars & set(existing)
                    union = t_chars | set(existing)
                    if union and len(intersection) / len(union) > 0.80:
                        duplicate = True
                        break
                if not duplicate:
                    seen_texts.append(t)
                    selected.append((
                        t,
                        src,
                        item.get("title", ""),
                    ))

        if not selected:
            return "无法从检索结果中提取有效内容生成答案"

        # Build answer: merge same-source chunks into continuous paragraphs
        source_groups: dict[str, list[str]] = {}
        for text, src, title in selected:
            source_groups.setdefault(src, []).append(text)

        paragraphs: list[str] = []
        for src in source_groups:
            merged = "".join(source_groups[src])
            paragraphs.append(merged)

        return "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    # load_knowledge_base
    # ------------------------------------------------------------------

    def load_knowledge_base(
        self,
        knowledge_dir: Path | str | None = None,
        db=None,
    ) -> int:
        """Batch-load all supported documents from a directory.

        This is a convenience method primarily used at startup to pre-populate
        the index from a static knowledge folder.

        Parameters
        ----------
        knowledge_dir : Path, str, or None
            Directory to scan.  Defaults to ``settings.knowledge_base_dir``.
        db : sqlite3.Connection or None
            Optional database connection for status updates.

        Returns
        -------
        int
            Total number of chunks added.
        """
        if knowledge_dir is None:
            knowledge_dir = settings.knowledge_base_dir
        knowledge_dir = Path(knowledge_dir)

        # Already loaded from cache — skip re-processing
        if self.vector_count > 0:
            return 0

        if not knowledge_dir.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {knowledge_dir}"
            )

        supported_exts = (".md", ".txt", ".pdf", ".docx")
        files = sorted(
            p for p in knowledge_dir.rglob("*")
            if p.suffix.lower() in supported_exts and p.is_file()
        )

        if not files:
            return 0

        total_chunks = 0
        for fp in files:
            # Use file name stem as a pseudo-document-id when no DB row exists
            pseudo_id = abs(hash(str(fp.resolve()))) % (2**31 - 1)
            try:
                # Relative path as source (e.g. "academic/xxx.md")
                rel_source = str(fp.relative_to(knowledge_dir))
                n = self.add_document(
                    file_path=fp,
                    document_id=pseudo_id,
                    title=fp.stem,
                    category="知识库",
                    source=rel_source,
                    db=db,
                )
                total_chunks += n
            except Exception:
                continue  # skip problematic files

        return total_chunks

    # ------------------------------------------------------------------
    # save_index  (explicit persist)
    # ------------------------------------------------------------------

    def save_index(self) -> None:
        """Explicitly persist the current FAISS index and chunk store."""
        self._save_cache()

    # ------------------------------------------------------------------
    # Stats / introspection
    # ------------------------------------------------------------------

    @property
    def chunk_count(self) -> int:
        """Number of chunks currently in the index."""
        return len(self._chunks)

    @property
    def vector_count(self) -> int:
        """Number of vectors in the FAISS index."""
        with self._index_lock:
            if self._index is not None:
                return self._index.ntotal
            return 0

    @property
    def is_ready(self) -> bool:
        """Whether the engine has an index with at least one vector."""
        return self.vector_count > 0


# Singleton instance — importable as ``from .rag_engine import rag_engine``
rag_engine = HHURAGEngine()
