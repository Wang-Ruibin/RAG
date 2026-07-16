from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.responses import success
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import Role
from app.models.orm import User
from app.models.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut

from .dependencies import CurrentUser, Database

router = APIRouter(prefix="/api/auth", tags=["认证"])


def token_payload(user: User) -> dict[str, object]:
    value = TokenOut(
        access_token=create_access_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )
    return value.model_dump(mode="json")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Database) -> dict[str, object]:
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册")
    user = User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role=Role.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success(token_payload(user), "注册成功", 201)


@router.post("/login")
def login(body: LoginRequest, db: Database) -> dict[str, object]:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return success(token_payload(user), "登录成功")


@router.get("/me")
def me(user: CurrentUser) -> dict[str, object]:
    return success(UserOut.model_validate(user).model_dump(mode="json"))
