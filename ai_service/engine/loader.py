"""
Document loader for the RAG engine.
Loads markdown/text documents from knowledge_docs/ directory.
"""

import hashlib
import os
import re
from pathlib import Path


def _read_file_with_bom_handling(file_path: str) -> str:
    """Read file content, handling UTF-8 BOM."""
    with open(file_path, "rb") as f:
        raw = f.read()
    # Strip UTF-8 BOM if present
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8")


def _clean_text(text: str) -> str:
    """Clean text content:
    - Strip boilerplate lines starting with ``上一篇：`` or ``下一篇：``
    - Strip navigation menu artifacts (lines with only ``|``, ``-``, whitespace)
    - Deduplicate consecutive empty lines
    - Strip leading/trailing whitespace per line
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Strip boilerplate navigation lines
        if stripped.startswith("上一篇：") or stripped.startswith("下一篇："):
            continue
        # Strip table/navigation artifacts (only |, -, and whitespace)
        if re.match(r"^[\s\|\-]+$", stripped):
            continue
        # Strip leading/trailing whitespace per line
        cleaned.append(stripped)

    # Deduplicate consecutive empty lines
    result = []
    prev_empty = False
    for line in cleaned:
        if line == "":
            if not prev_empty:
                result.append(line)
                prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return "\n".join(result).strip()


def _extract_title(content: str, filename: str) -> str:
    """Extract title from content.
    Prefer the first ``# Title`` (h1) from content; fall back to filename.
    """
    for line in content.splitlines():
        stripped = line.strip()
        # Match h1 headings but not h2+
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    # Fallback: filename without extension
    return Path(filename).stem


def _extract_source_url(content: str) -> str:
    """Extract source URL from ``> 来源:`` or ``> 来源：`` pattern."""
    match = re.search(r">\s*来源[：:]\s*(https?://\S+)", content)
    if match:
        return match.group(1).rstrip(")")
    return ""


def _compute_doc_id(file_path: str) -> str:
    """Compute md5 hex digest from the absolute file path."""
    absolute = os.path.abspath(file_path)
    return hashlib.md5(absolute.encode("utf-8")).hexdigest()


def _build_doc(file_path: str) -> dict:
    """Build a document dict from a file path.

    Returns
    -------
    dict
        ``{"doc_id", "title", "content", "category", "source_url", "file_path"}``
    """
    path = Path(file_path)
    raw = _read_file_with_bom_handling(file_path)
    content = _clean_text(raw)
    title = _extract_title(raw, path.name)
    source_url = _extract_source_url(raw)
    doc_id = _compute_doc_id(file_path)
    category = path.parent.name  # immediate parent directory name

    return {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "category": category,
        "source_url": source_url,
        "file_path": str(path.absolute()),
    }


def load_knowledge_docs(knowledge_dir: str | None = None) -> list[dict]:
    """Load all knowledge documents from the *knowledge_docs* directory.

    Parameters
    ----------
    knowledge_dir : str, optional
        Path to the knowledge docs directory.  When ``None`` (default) it is
        resolved relative to ``ai_service/engine/``:
        ``<repo_root>/knowledge_docs/``.

    Returns
    -------
    list[dict]
        Each dict has keys ``doc_id``, ``title``, ``content``, ``category``,
        ``source_url``, ``file_path``.

    Raises
    ------
    FileNotFoundError
        If *knowledge_dir* does not exist.
    """
    if knowledge_dir is None:
        knowledge_dir = os.path.join(
            os.path.dirname(__file__), "../../knowledge_docs"
        )
    knowledge_dir = os.path.abspath(knowledge_dir)

    if not os.path.isdir(knowledge_dir):
        raise FileNotFoundError(
            f"Knowledge directory not found: {knowledge_dir}"
        )

    docs = []
    md_files = sorted(Path(knowledge_dir).rglob("*.md"))

    for md_path in md_files:
        file_path = str(md_path)

        # Skip files that are too small (empty / minimal)
        if os.path.getsize(file_path) < 50:
            continue

        docs.append(_build_doc(file_path))

    return docs


def load_file(file_path: str) -> dict:
    """Load a single file and return it in the same dict format.

    Parameters
    ----------
    file_path : str
        Path to the file.  Supported extensions: ``.md``, ``.txt``.

    Returns
    -------
    dict
        Same schema as :func:`load_knowledge_docs`.

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    ValueError
        If the file extension is not supported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in (".md", ".txt"):
        raise ValueError(
            f"Unsupported file type: '{ext}'. "
            f"Only .md and .txt files are supported."
        )

    return _build_doc(file_path)


def get_doc_count(knowledge_dir: str | None = None) -> int:
    """Return the total number of documents in *knowledge_docs*.

    Parameters
    ----------
    knowledge_dir : str, optional
        Passed through to :func:`load_knowledge_docs`.

    Returns
    -------
    int
    """
    return len(load_knowledge_docs(knowledge_dir))
