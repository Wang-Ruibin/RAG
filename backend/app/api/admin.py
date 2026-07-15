from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.responses import success
from app.models.orm import User
from app.models.schemas import UserOut, UserUpdateRequest

from .dependencies import AdminUser, Database

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/users")
def list_users(db: Database, _admin: AdminUser) -> dict[str, object]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return success([UserOut.model_validate(user).model_dump(mode="json") for user in users])


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Database,
    admin: AdminUser,
) -> dict[str, object]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前管理员")
    if user.id == admin.id and body.role is not None and body.role != admin.role:
        raise HTTPException(status_code=400, detail="不能降低当前管理员角色")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(mode="json"), "用户已更新")
