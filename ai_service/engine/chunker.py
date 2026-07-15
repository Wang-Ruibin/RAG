"""
Document chunker for the RAG engine.

Splits documents (from loader) into overlapping chunks using LangChain's
RecursiveCharacterTextSplitter with Chinese-aware separators.
"""

from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_CHUNK_SIZE = 500
_DEFAULT_CHUNK_OVERLAP = 50

# Chinese-aware separator priority: paragraph → line → sentence → word
_CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    "，",
    " ",
    "",
]


def _make_splitter(
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """Build a configured RecursiveCharacterTextSplitter."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_CHINESE_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_docs(
    docs: list[dict],
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """Split a list of documents into overlapping text chunks.

    Parameters
    ----------
    docs : list[dict]
        Documents returned by ``loader.load_knowledge_docs`` or
        ``loader.load_file``.  Each dict must contain at least the keys
        ``doc_id``, ``title``, ``content``, ``category``, ``source_url``.
    chunk_size : int
        Maximum number of characters per chunk (default 500).
    chunk_overlap : int
        Number of overlapping characters between consecutive chunks
        (default 50).

    Returns
    -------
    list[dict]
        Each chunk dict: ``{content, doc_id, chunk_index, title, category,
        source_url}``.
    """
    splitter = _make_splitter(chunk_size, chunk_overlap)
    all_chunks: list[dict] = []

    for doc in docs:
        content = doc.get("content", "")
        if not content:
            continue

        raw_chunks = splitter.split_text(content)

        for i, chunk_text in enumerate(raw_chunks):
            all_chunks.append(
                {
                    "content": chunk_text,
                    "doc_id": doc["doc_id"],
                    "chunk_index": i,
                    "title": doc["title"],
                    "category": doc.get("category", ""),
                    "source_url": doc.get("source_url", ""),
                }
            )

    return all_chunks


def chunk_text(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split a plain text string into chunks (no metadata wrapping).

    Parameters
    ----------
    text : str
        The text to split.
    chunk_size, chunk_overlap : int
        Passed through to ``RecursiveCharacterTextSplitter``.

    Returns
    -------
    list[str]
        List of text chunks.  Empty list when *text* is empty.
    """
    if not text:
        return []

    splitter = _make_splitter(chunk_size, chunk_overlap)
    return splitter.split_text(text)


def get_stats(chunks: list[dict]) -> dict[str, Any]:
    """Compute aggregate statistics over a list of chunk dicts.

    Parameters
    ----------
    chunks : list[dict]
        Output from :func:`chunk_docs`.

    Returns
    -------
    dict
        Keys: ``total_chunks``, ``avg_chunk_length``, ``min_length``,
        ``max_length``, ``total_docs``.
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "avg_chunk_length": 0.0,
            "min_length": 0,
            "max_length": 0,
            "total_docs": 0,
        }

    lengths = [len(c["content"]) for c in chunks]
    doc_ids = {c["doc_id"] for c in chunks}

    return {
        "total_chunks": len(chunks),
        "avg_chunk_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_docs": len(doc_ids),
    }
