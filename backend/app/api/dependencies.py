from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.config import settings
from app.models.enums import Role
from app.models.orm import User

bearer = HTTPBearer(auto_error=False)
Database = Annotated[Session, Depends(get_db)]


def _has_java_perm(request: Request, *perms: str) -> bool:
    """检查请求头中的 Java 权限是否包含任一指定权限。"""
    perm_header = request.headers.get("X-Login-Perms", "")
    user_perms = {p.strip() for p in perm_header.split(",") if p.strip()}
    roles_header = request.headers.get("X-Login-Roles", "")
    user_roles = {r.strip() for r in roles_header.split(",") if r.strip()}
    # admin 角色拥有所有权限
    if "admin" in user_roles:
        return True
    return bool(user_perms & set(perms))


def require_perm(*perms: str):
    """返回一个 FastAPI 依赖：登录 + 权限校验一步完成。"""

    def checker(db: Database, request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
        user = current_user(db, request, credentials)
        if user.role == Role.ADMIN or _has_java_perm(request, *perms):
            return user
        raise HTTPException(status_code=403, detail="权限不足")

    return checker


def current_user(
    db: Database,
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    # ── 网关信任模式（生产环境） ──
    # Gateway 鉴权通过后注入 X-Login-Name（Java 登录名），Python 按名查找或创建影子用户
    login_name = request.headers.get("X-Login-Name")
    if login_name:
        if login_name == settings.guest_login_name:
            # 访客：不查库、不建影子用户，返回不落库的内存 User（id=None 即 is_guest_user 判定依据）。
            # 字段必须显式给全：transient 对象不触发列默认值，缺省的 is_active 会是 None 导致误判停用。
            return User(
                name=login_name,
                email="guest@campusqa.internal",
                password_hash="",
                role=Role.STUDENT,
                is_active=True,
            )
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


def admin_user(user: CurrentUser, request: Request) -> User:
    # Python 自身角色为 ADMIN，或 Java 角色中包含 admin（角色管理分配的）
    if user.role == Role.ADMIN or _has_java_admin(request):
        return user
    raise HTTPException(status_code=403, detail="需要管理员权限")


AdminUser = Annotated[User, Depends(admin_user)]
