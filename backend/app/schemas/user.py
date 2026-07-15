"""用户相关 Pydantic 模型"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    email: str | None = Field(None, max_length=100, description="邮箱")
    role: str = Field("student", pattern="^(student|teacher|admin)$", description="角色")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    nickname: str | None = None
    email: str | None = None
    avatar: str | None = None


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    nickname: str | None
    email: str | None
    role: str
    avatar: str | None
    status: int
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT 令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None
