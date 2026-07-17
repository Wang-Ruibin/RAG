from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import Role
from app.models.orm import User

bearer_scheme = HTTPBearer(auto_error=False)
Database = Annotated[Session, Depends(get_db)]


def current_user(
    db: Database,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    # ── 网关信任模式（生产环境） ──
    # Gateway 鉴权通过后注入 X-Login-Name（Java 登录名），Python 按名查找或创建影子用户
    login_name = request.headers.get("X-Login-Name")
    if login_name:
        user = db.scalars(select(User).where(User.name == login_name)).first()
        if user is None:
            # find-or-create 影子用户，role 默认 STUDENT
            user = User(
                name=login_name,
                email=f"gw_{login_name}@campusqa.internal",
                password_hash="",
                role=Role.STUDENT,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if not user.is_active:
            raise HTTPException(status_code=401, detail="账号已禁用")
        return user

    # ── Bearer Token 模式（开发环境直接访问 Python） ──
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")
    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=401, detail="登录状态已失效")
    user = db.get(User, int(str(payload["sub"])))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="账号不可用")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


AdminUser = Annotated[User, Depends(admin_user)]
