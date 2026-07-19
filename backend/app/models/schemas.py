from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .enums import (
    AnswerCorrectionStatus,
    AnswerKnowledgeStatus,
    AnswerOrigin,
    DocumentKind,
    DocumentStatus,
    MessageStatus,
    ProcessingStage,
    Role,
)


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
    document_kind: DocumentKind
    contributor_name: str | None
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
    source_type: str | None = None
    chunk_id: int | None = None
    document_id: int | None = None
    title: str
    url: str | None = None
    source_url: str | None = None
    published_at: date | None = None
    score: float | None = None
    snippet: str
    content: str | None = None
    site_name: str | None = None
    domain: str | None = None
    citation_index: int | None = None
    contributor_name: str | None = None


class DocumentPreviewOut(BaseModel):
    content: str
    offset: int
    limit: int
    total_chars: int
    has_more: bool
    format: str


class AnswerCorrectionSubmitRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    corrected_answer: str = Field(min_length=2, max_length=6000)


class AnswerCorrectionApproveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=2, max_length=1000)
    answer: str = Field(min_length=2, max_length=6000)
    source_document_ids: list[int] = Field(default_factory=list, max_length=20)


class AnswerCorrectionRejectRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(min_length=2, max_length=1000)


class AnswerCorrectionOut(BaseModel):
    id: int
    assistant_message_id: int | None
    status: AnswerCorrectionStatus
    proposed_answer: str
    reviewed_question: str | None = None
    reviewed_answer: str | None = None
    review_note: str | None = None
    approved_document_id: int | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: int | None = None


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("会话标题不能为空")
        return title


class ChatResult(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[SourceRef]
    answer_origin: AnswerOrigin
    model: str
    latency_ms: int


class AnswerKnowledgeTaskOut(BaseModel):
    id: int
    assistant_message_id: int
    status: AnswerKnowledgeStatus
    document_id: int | None = None
    qa_entry_id: int | None = None
    cleaned_title: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict[str, Any]]
    status: MessageStatus
    model: str | None
    latency_ms: int | None
    answer_origin: AnswerOrigin | None = None
    knowledge_task: AnswerKnowledgeTaskOut | None = None
    correction: AnswerCorrectionOut | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] | None = None
