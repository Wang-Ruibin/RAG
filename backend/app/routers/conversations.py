"""Conversation history management router.

Users can list, view, and delete their own conversations.
All operations are scoped to the authenticated user's own data.
"""

from typing import Annotated
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from .auth import current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---------------------------------------------------------------------------
# GET /api/conversations — list current user's conversations
# ---------------------------------------------------------------------------


@router.get("")
def list_conversations(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    user: Annotated[sqlite3.Row, Depends(current_user)],
) -> list[dict]:
    """Return all conversations belonging to the current user, newest first."""
    rows = db.execute(
        """
        SELECT c.*, COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.updated_at DESC
        """,
        (user["id"],),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/conversations/{conversation_id} — single conversation with messages
# ---------------------------------------------------------------------------


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    user: Annotated[sqlite3.Row, Depends(current_user)],
) -> dict:
    """Return a single conversation with its messages, sources parsed as lists."""
    conv = db.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user["id"]),
    ).fetchone()

    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()

    return {
        "id": conv["id"],
        "user_id": conv["user_id"],
        "title": conv["title"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "messages": [
            {
                "id": m["id"],
                "conversation_id": m["conversation_id"],
                "role": m["role"],
                "content": m["content"],
                "sources": json.loads(m["sources"]),
                "created_at": m["created_at"],
            }
            for m in messages
        ],
    }


# ---------------------------------------------------------------------------
# DELETE /api/conversations/{conversation_id} — delete conversation (CASCADE)
# ---------------------------------------------------------------------------


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    user: Annotated[sqlite3.Row, Depends(current_user)],
) -> None:
    """Delete a conversation and its messages (via ON DELETE CASCADE)."""
    cursor = db.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user["id"]),
    )
    db.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="对话不存在")
