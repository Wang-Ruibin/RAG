"""User management router (admin only) and public stats endpoint."""

from typing import Annotated
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..models import StatsResponse, UserUpdateBody
from .auth import admin_user, current_user, public_user

router = APIRouter(prefix="/api/users", tags=["users"])
stats_router = APIRouter(prefix="/api", tags=["stats"])

_VALID_ROLES = frozenset({"STUDENT", "ADMIN"})


# ---------------------------------------------------------------------------
# GET /api/users — list all users (admin only)
# ---------------------------------------------------------------------------


@router.get("")
def list_users(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> list[dict]:
    """Return every user ordered by creation date, newest first."""
    rows = db.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [public_user(r) for r in rows]


# ---------------------------------------------------------------------------
# PATCH /api/users/{user_id} — update user (admin only)
# ---------------------------------------------------------------------------


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateBody,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Update a user's role or active status."""
    row = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    # Prevent an admin from disabling their own account
    if body.is_active is False and row["id"] == admin["id"]:
        raise HTTPException(status_code=400, detail="不能停用当前管理员")

    # Validate role if provided
    if body.role is not None and body.role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail="角色无效")

    # Build dynamic UPDATE statement for only the provided fields
    fields: list[str] = []
    params: list = []
    if body.role is not None:
        fields.append("role = ?")
        params.append(body.role)
    if body.is_active is not None:
        fields.append("is_active = ?")
        params.append(1 if body.is_active else 0)

    if fields:
        params.append(user_id)
        db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        db.commit()

    # Return refreshed user
    updated = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return public_user(updated)


# ---------------------------------------------------------------------------
# DELETE /api/users/{user_id} — delete user (admin only)
# ---------------------------------------------------------------------------


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    admin: Annotated[dict, Depends(admin_user)],
) -> None:
    """Delete a user and all their data (admin only).

    - Cannot delete yourself (admin user cannot self-delete)
    - Deletes user's documents (cascades to chunks)
    - Cascades to conversations and messages
    - Returns 404 if user not found
    """
    row = db.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    # Prevent self-deletion
    if row["id"] == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前管理员账号")

    # Delete documents by this user (cascades to chunks via FK)
    db.execute("DELETE FROM documents WHERE uploaded_by = ?", (user_id,))

    # Delete the user (cascades to conversations → messages via FK)
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))

    db.commit()


# ---------------------------------------------------------------------------
# GET /api/stats — platform statistics (any authenticated user)
# ---------------------------------------------------------------------------


@stats_router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _user: Annotated[dict, Depends(current_user)],
) -> dict:
    """Return platform-wide counts for documents, chunks, and conversations."""
    from ..rag_engine import rag_engine

    doc_count = db.execute(
        "SELECT COUNT(*) AS cnt FROM documents WHERE status = 'READY'"
    ).fetchone()["cnt"]

    conv_count = db.execute(
        "SELECT COUNT(*) AS cnt FROM conversations"
    ).fetchone()["cnt"]

    chunk_count = (
        len(rag_engine.chunks)
        if hasattr(rag_engine, "chunks")
        else 0
    )

    return {
        "documents": doc_count,
        "chunks": chunk_count,
        "conversations": conv_count,
    }
