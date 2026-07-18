"""Cache management router: view, delete single, and flush all Q&A cache entries.

All endpoints require ADMIN privileges.
"""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from .auth import admin_user

router = APIRouter(prefix="/api/cache", tags=["cache"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_cache(
    db: sqlite3.Connection = Depends(get_db),
    _admin: sqlite3.Row = Depends(admin_user),
) -> list[dict]:
    """Return all cached Q&A entries, ordered by hit_count descending.

    Each entry includes parsed sources (JSON string → list).
    """
    rows = db.execute(
        """SELECT id, question, answer, sources, hit_count, created_at, updated_at
           FROM qa_cache
           ORDER BY hit_count DESC""",
    ).fetchall()

    result = []
    for row in rows:
        entry = dict(row)
        try:
            entry["sources"] = json.loads(entry["sources"])
        except (json.JSONDecodeError, TypeError):
            entry["sources"] = []
        result.append(entry)

    return result


@router.delete("/{cache_id}", status_code=204)
def delete_cache_entry(
    cache_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _admin: sqlite3.Row = Depends(admin_user),
) -> None:
    """Delete a single cached Q&A entry by its id.

    Returns 204 on success, 404 if the entry does not exist.
    """
    cursor = db.execute("DELETE FROM qa_cache WHERE id = ?", (cache_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="缓存条目不存在")


@router.delete("")
def flush_cache(
    db: sqlite3.Connection = Depends(get_db),
    _admin: sqlite3.Row = Depends(admin_user),
) -> dict:
    """Delete every Q&A cache entry.

    Returns the number of deleted rows as ``{"count": N}``.
    """
    cursor = db.execute("DELETE FROM qa_cache")
    db.commit()
    return {"count": cursor.rowcount}


__all__ = ["router"]
