from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .enums import DocumentStatus, MessageStatus, ProcessingStage, Role


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserUpdateRequest(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_name: str
    mime_type: str
    size: int
    category: str
    source_url: str | None
    published_at: date | None
    status: DocumentStatus
    stage: ProcessingStage
    error: str | None
    chunk_count: int
    uploaded_by: int
    created_at: datetime
    updated_at: datetime


class DocumentUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=100)
    source_url: str | None = Field(default=None, max_length=1200)
    published_at: date | None = None


class SourceRef(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    source_url: str | None = None
    published_at: date | None = None
    score: float
    snippet: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: int | None = None
    use_agent: bool = False


class ChatResult(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[SourceRef]
    model: str
    latency_ms: int


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict[str, Any]]
    status: MessageStatus
    model: str | None
    latency_ms: int | None
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] | None = None
