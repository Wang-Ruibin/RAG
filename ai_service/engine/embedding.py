"""
Embedding service for the RAG engine.

Uses ``sentence-transformers`` with ``BAAI/bge-small-zh-v1.5`` to produce
384-dimensional normalized embeddings on CPU.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

DIMENSION: int = 512
"""Output dimension of the embedding model (``BAAI/bge-small-zh-v1.5`` uses 512d)."""

MODEL_NAME: str = "BAAI/bge-small-zh-v1.5"
"""HuggingFace model identifier used for embeddings."""

# ---------------------------------------------------------------------------
# Lazy singleton (module-level)
# ---------------------------------------------------------------------------

_model = None


def get_model():
    """Return the SentenceTransformer singleton, loading it on first call.

    The model is cached in a module-level global so that subsequent calls
    incur no download or reload cost.  Logging output from the underlying
    ``sentence-transformers`` library is suppressed to keep the console
    clean.

    Returns
    -------
    SentenceTransformer
    """
    global _model
    if _model is not None:
        return _model

    # Suppress sentence-transformers & transformers verbose logging on load
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(
        MODEL_NAME,
        device="cpu",
        cache_folder=None,  # use default HuggingFace cache
    )
    # NOTE: normalize_embeddings=True is set at encode-time (see embed())
    logger.info("Loaded embedding model: %s (dim=%d)", MODEL_NAME, DIMENSION)
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed(texts: str | list[str]) -> np.ndarray:
    """Embed one or more texts into a 2-D numpy array.

    Parameters
    ----------
    texts : str | list[str]
        A single string or a list of strings to embed.

    Returns
    -------
    np.ndarray
        Shape ``(len(texts), DIMENSION)``, dtype ``float32``, L2-normalized rows.

    Examples
    --------
    >>> embed("hello").shape
    (1, 512)
    >>> embed([]).shape
    (0, 512)
    """
    # Normalise input to a list
    if isinstance(texts, str):
        texts = [texts]

    if len(texts) == 0:
        return np.empty((0, DIMENSION), dtype=np.float32)

    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=np.float32)


def embed_query(text: str, use_instruction: bool = False) -> np.ndarray:
    """Embed a single query string.

    When *use_instruction* is ``True`` the text is prefixed with the BGE
    instruction template ``"为这个句子生成表示以用于检索相关文章："``, which
    is recommended for asymmetric retrieval tasks.

    Parameters
    ----------
    text : str
        The query string.
    use_instruction : bool, optional
        Whether to prepend the BGE retrieval instruction (default ``False``).

    Returns
    -------
    np.ndarray
        Shape ``(1, DIMENSION)``, dtype ``float32``, L2-normalised.
    """
    if use_instruction:
        text = f"为这个句子生成表示以用于检索相关文章：{text}"
    return embed([text])
