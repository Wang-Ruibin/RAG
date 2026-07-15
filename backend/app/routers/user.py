"""用户相关 API 路由"""

import time

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/api/user", tags=["用户管理"])


def _success(data=None, message="success"):
    """统一成功响应"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


def _error(code: int, message: str):
    """统一错误响应"""
    return {
        "code": code,
        "message": message,
        "data": None,
        "timestamp": int(time.time()),
    }


def _get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> int:
    """从 JWT 令牌中解析当前用户ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="认证令牌格式错误")

    payload = UserService.decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="认证令牌无效")

    return user_id


@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        user = UserService.register(db, data)
        return _success(
            data=UserResponse.model_validate(user).model_dump(),
            message="注册成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        user = UserService.login(db, data.username, data.password)
        token = UserService.create_access_token(
            {"user_id": user.id, "username": user.username, "role": user.role}
        )
        return _success(
            data=Token(
                access_token=token,
                user=UserResponse.model_validate(user),
            ).model_dump(),
            message="登录成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile")
def get_profile(
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """获取个人信息"""
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _success(data=UserResponse.model_validate(user).model_dump())


@router.put("/profile")
def update_profile(
    data: UserUpdate,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """更新个人信息"""
    user = UserService.update_profile(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _success(
        data=UserResponse.model_validate(user).model_dump(),
        message="更新成功",
    )


@router.get("/list")
def get_user_list(
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
    status: int | None = None,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """管理员获取用户列表"""
    # 验证权限
    current_user = UserService.get_by_id(db, user_id)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限访问")

    users, total = UserService.get_user_list(
        db, page=page, page_size=page_size, role=role, status=status
    )
    return _success(
        data={
            "total": total,
            "items": [UserResponse.model_validate(u).model_dump() for u in users],
            "page": page,
            "page_size": page_size,
        }
    )


@router.put("/{target_user_id}/role")
def admin_update_role(
    target_user_id: int,
    role: str,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """管理员修改用户角色"""
    current_user = UserService.get_by_id(db, user_id)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限访问")
    if role not in ("student", "teacher", "admin"):
        raise HTTPException(status_code=400, detail="无效的角色: 必须是 student/teacher/admin")
    target = UserService.get_by_id(db, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.role = role
    db.commit()
    db.refresh(target)
    return _success(
        data=UserResponse.model_validate(target).model_dump(),
        message="角色已更新",
    )


@router.put("/{target_user_id}/status")
def admin_update_status(
    target_user_id: int,
    status: int,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """管理员启用/禁用用户"""
    current_user = UserService.get_by_id(db, user_id)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限访问")
    if status not in (0, 1):
        raise HTTPException(status_code=400, detail="无效的状态: 0=禁用, 1=启用")
    target = UserService.get_by_id(db, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.status = status
    db.commit()
    db.refresh(target)
    return _success(
        data=UserResponse.model_validate(target).model_dump(),
        message="启用" if status == 1 else "已禁用",
    )
