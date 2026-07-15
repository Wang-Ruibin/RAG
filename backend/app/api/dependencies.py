from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import Role
from app.models.orm import User

bearer = HTTPBearer(auto_error=False)
Database = Annotated[Session, Depends(get_db)]


def current_user(
    db: Database,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
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
