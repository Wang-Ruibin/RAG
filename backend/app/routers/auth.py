"""Authentication router: register, login, guest login, and current-user lookup."""

from typing import Annotated
import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from ..database import get_db, utc_now
from ..security import create_token, decode_token, hash_password, verify_password
from ..models import RegisterBody, LoginBody

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def public_user(row: sqlite3.Row) -> dict:
    """Return a safe user dict (no password_hash, no internal fields)."""
    return {
        "id": row["id"],
        "name": row["name"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def current_user(
    db: sqlite3.Connection = Depends(get_db),
    authorization: str | None = Header(None),
) -> sqlite3.Row:
    """Extract and validate the authenticated user from the JWT bearer token."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录")

    token = authorization.removeprefix("Bearer ")
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)
    ).fetchone()

    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="账号已被禁用")

    return user


def admin_user(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    """Require the current user to have ADMIN role."""
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
def register(
    body: RegisterBody,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Register a new student account."""
    username = body.username

    existing = db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing is not None:
        raise HTTPException(status_code=409, detail="该用户名已被注册")

    now = utc_now()
    cursor = db.execute(
        """INSERT INTO users (name, username, password_hash, role, is_active, created_at)
           VALUES (?, ?, ?, 'STUDENT', 1, ?)""",
        (body.name, username, hash_password(body.password), now),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    token = create_token(row["id"], row["role"])

    return {"token": token, "user": public_user(row)}


@router.post("/login")
def login(
    body: LoginBody,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Authenticate with username and password."""
    username = body.username

    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user is None or not verify_password(body.password, user["password_hash"]):
        # Merged error to prevent username enumeration
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_token(user["id"], user["role"])
    return {"token": token, "user": public_user(user)}


@router.post("/guest")
def guest(
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create a temporary guest account."""
    guest_key = uuid.uuid4().hex[:12]
    username = f"guest-{guest_key}"
    now = utc_now()

    cursor = db.execute(
        """INSERT INTO users (name, username, password_hash, role, is_active, created_at)
           VALUES (?, ?, ?, 'STUDENT', 1, ?)""",
        ("访客", username, hash_password(guest_key), now),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    token = create_token(row["id"], row["role"])

    return {"token": token, "user": public_user(row)}


@router.get("/me")
def me(
    current_user: sqlite3.Row = Depends(current_user),
) -> dict:
    """Return the currently authenticated user."""
    return public_user(current_user)


__all__ = ["router", "current_user", "admin_user", "public_user"]
