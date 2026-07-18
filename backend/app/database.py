"""SQLite database setup, schema, migrations, and connection helpers.

Uses raw sqlite3 (no ORM). Connection management via a FastAPI-compatible
generator dependency and a context-managed transaction helper.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from .config import settings

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    is_system INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'STUDENT',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROCESSING' CHECK(status IN ('PROCESSING', 'READY', 'ERROR')),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    source_url TEXT DEFAULT '',
    category TEXT DEFAULT '其他',
    error TEXT,
    uploaded_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(uploaded_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    vector BLOB,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('USER', 'ASSISTANT')),
    content TEXT NOT NULL,
    sources TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS qa_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_signature TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT NOT NULL DEFAULT '[]',
    hit_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_qa_cache_signature ON qa_cache(question_signature);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string (second precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open a new SQLite connection with sensible defaults.

    Parameters
    ----------
    path : Path, str, or None
        Database file path.  Defaults to ``settings.database_path``.

    Returns
    -------
    sqlite3.Connection
        Connection with ``sqlite3.Row`` factory, WAL journal mode,
        10 s busy timeout, and foreign keys enabled.
    """
    if path is None:
        path = settings.database_path
    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ---------------------------------------------------------------------------
# FastAPI generator dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI ``Depends`` generator yielding an open connection.

    The connection is automatically closed when the request finishes.
    """
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Transaction context manager
# ---------------------------------------------------------------------------

@contextmanager
def transaction(path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that commits on success, rolls back on exception.

    Usage::

        with transaction() as db:
            db.execute("INSERT INTO users ...")
            db.execute("UPDATE documents ...")
    """
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Startup initialisation
# ---------------------------------------------------------------------------

def init_database(path: Path | None = None) -> None:
    """Create all tables and indexes defined in ``SCHEMA``.

    Safe to call repeatedly (``CREATE TABLE IF NOT EXISTS`` /
    ``CREATE INDEX IF NOT EXISTS``).

    Called once during application startup.
    """
    with transaction(path) as db:
        db.executescript(SCHEMA)
