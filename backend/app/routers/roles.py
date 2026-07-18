"""Role management router (admin only).

Provides CRUD operations for user roles backed by the ``roles`` table.
"""

from typing import Annotated
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db, utc_now
from ..models import RoleCreateBody, RoleUpdateBody
from .auth import admin_user

router = APIRouter(prefix="/api/roles", tags=["roles"])


# ---------------------------------------------------------------------------
# GET /api/roles — list all roles with user count
# ---------------------------------------------------------------------------


@router.get("")
def list_roles(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> list[dict]:
    """Return every role with its user count, ordered by creation date."""
    rows = db.execute("""
        SELECT r.*, COALESCE(u.user_count, 0) AS user_count
        FROM roles r
        LEFT JOIN (
            SELECT role, COUNT(*) AS user_count
            FROM users
            GROUP BY role
        ) u ON u.role = r.name
        ORDER BY r.created_at ASC
    """).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/roles/{name} — role detail with user list
# ---------------------------------------------------------------------------


@router.get("/{name}")
def get_role(
    name: str,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Return role details and the list of users who have this role."""
    role = db.execute(
        "SELECT * FROM roles WHERE name = ?", (name,)
    ).fetchone()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    users = db.execute(
        "SELECT id, name, username, is_active, created_at FROM users WHERE role = ?",
        (name,),
    ).fetchall()

    result = dict(role)
    result["users"] = [dict(u) for u in users]
    return result


# ---------------------------------------------------------------------------
# POST /api/roles — create new role
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_role(
    body: RoleCreateBody,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Create a new custom role (name must be at least 2 characters)."""
    name = body.name.strip().upper()
    if not name:
        raise HTTPException(status_code=400, detail="角色名称不能为空")

    existing = db.execute(
        "SELECT id FROM roles WHERE name = ?", (name,)
    ).fetchone()
    if existing is not None:
        raise HTTPException(status_code=409, detail="该角色名称已存在")

    now = utc_now()
    db.execute(
        """INSERT INTO roles (name, description, is_system, created_at)
           VALUES (?, ?, 0, ?)""",
        (name, body.description.strip(), now),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM roles WHERE name = ?", (name,)
    ).fetchone()
    return dict(row)


# ---------------------------------------------------------------------------
# PATCH /api/roles/{name} — update role description
# ---------------------------------------------------------------------------


@router.patch("/{name}")
def update_role(
    name: str,
    body: RoleUpdateBody,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Update the description of an existing role."""
    role = db.execute(
        "SELECT * FROM roles WHERE name = ?", (name,)
    ).fetchone()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    db.execute(
        "UPDATE roles SET description = ? WHERE name = ?",
        (body.description.strip(), name),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM roles WHERE name = ?", (name,)
    ).fetchone()
    return dict(row)


# ---------------------------------------------------------------------------
# DELETE /api/roles/{name} — delete role (system roles cannot be deleted)
# ---------------------------------------------------------------------------


@router.delete("/{name}")
def delete_role(
    name: str,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    _admin: Annotated[dict, Depends(admin_user)],
) -> dict:
    """Delete a role.

    System roles (is_system=1) cannot be deleted.
    Users assigned to the deleted role will be reassigned to STUDENT.
    """
    role = db.execute(
        "SELECT * FROM roles WHERE name = ?", (name,)
    ).fetchone()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role["is_system"]:
        raise HTTPException(status_code=400, detail="系统角色不能删除")

    # Reassign users with this role to STUDENT
    db.execute(
        "UPDATE users SET role = 'STUDENT' WHERE role = ?",
        (name,),
    )

    db.execute("DELETE FROM roles WHERE name = ?", (name,))
    db.commit()

    return {"detail": f"角色 {name} 已删除，相关用户已转为 STUDENT"}
