import re
from pydantic import BaseModel, Field, field_validator


_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fff]+$")


class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=6, max_length=72)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_PATTERN.match(v):
            raise ValueError("用户名只允许字母、数字、下划线和中文")
        return v


class LoginBody(BaseModel):
    username: str = Field(min_length=1)
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 1:
            raise ValueError("用户名至少1个字符")
        return v


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserUpdateBody(BaseModel):
    role: str | None = None  # "STUDENT" | "ADMIN"
    is_active: bool | None = None


class ChatBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    stored_name: str
    mime_type: str
    size: int
    status: str
    chunk_count: int
    source_url: str | None = None
    category: str | None = None
    error: str | None = None
    uploaded_by: int
    uploader_name: str | None = None
    created_at: str
    updated_at: str


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message_count: int = 0
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str  # "USER" | "ASSISTANT"
    content: str
    sources: list = []
    created_at: str


class StatsResponse(BaseModel):
    documents: int
    chunks: int
    conversations: int


class RoleCreateBody(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=200)


class RoleUpdateBody(BaseModel):
    description: str = Field(max_length=200)


class HealthResponse(BaseModel):
    status: str
    mode: str
    version: str
