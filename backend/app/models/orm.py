from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from .enums import (
    AnswerCorrectionStatus,
    AnswerKnowledgeStatus,
    AnswerOrigin,
    DocumentKind,
    DocumentStatus,
    MessageRole,
    MessageStatus,
    ProcessingStage,
    Role,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.STUDENT, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    documents: Mapped[list[Document]] = relationship(back_populates="uploader")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    original_name: Mapped[str] = mapped_column(String(500))
    stored_name: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120), default="text/plain")
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    category: Mapped[str] = mapped_column(String(100), default="其他", index=True)
    document_kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind), default=DocumentKind.KNOWLEDGE_BASE, index=True
    )
    contributor_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1200), nullable=True)
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.QUEUED, index=True
    )
    stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage), default=ProcessingStage.SAVED
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    uploader: Mapped[User] = relationship(back_populates="documents")
    jobs: Mapped[list[IngestionJob]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.QUEUED
    )
    stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage), default=ProcessingStage.SAVED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[Document] = relationship(back_populates="jobs")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text, default="")
    sources_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.COMPLETE
    )
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_origin: Mapped[AnswerOrigin | None] = mapped_column(
        Enum(AnswerOrigin), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AnswerKnowledgeTask(Base):
    __tablename__ = "answer_knowledge_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    assistant_message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), unique=True, index=True
    )
    source_answer_origin: Mapped[AnswerOrigin | None] = mapped_column(
        Enum(AnswerOrigin), nullable=True
    )
    original_question: Mapped[str] = mapped_column(Text)
    original_answer: Mapped[str] = mapped_column(Text)
    sources_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    cleaned_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cleaned_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    qa_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("qa_entries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[AnswerKnowledgeStatus] = mapped_column(
        Enum(AnswerKnowledgeStatus), default=AnswerKnowledgeStatus.QUEUED, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QaEntry(Base):
    """Metadata for a hidden, separately indexed, user-approved QA entry."""

    __tablename__ = "qa_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    question_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_answer_origin: Mapped[AnswerOrigin | None] = mapped_column(
        Enum(AnswerOrigin), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class QaSourceLink(Base):
    """Stable provenance edge from a hidden QA entry to a visible knowledge document."""

    __tablename__ = "qa_source_links"
    __table_args__ = (UniqueConstraint("qa_entry_id", "document_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    qa_entry_id: Mapped[int] = mapped_column(
        ForeignKey("qa_entries.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    source_chunk_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    marker: Mapped[str] = mapped_column(String(1), default="S")
    citation_index: Mapped[int] = mapped_column(Integer)
    source_kind: Mapped[str] = mapped_column(String(32), default="KNOWLEDGE_BASE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AnswerCorrection(Base):
    __tablename__ = "answer_corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assistant_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    contributor_name: Mapped[str] = mapped_column(String(80))
    contributor_email: Mapped[str] = mapped_column(String(255))
    original_question: Mapped[str] = mapped_column(Text)
    original_answer: Mapped[str] = mapped_column(Text)
    original_sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    proposed_answer: Mapped[str] = mapped_column(Text)
    reviewed_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AnswerCorrectionStatus] = mapped_column(
        Enum(AnswerCorrectionStatus), default=AnswerCorrectionStatus.PENDING, index=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CorrectionSourceLink(Base):
    __tablename__ = "correction_source_links"
    __table_args__ = (UniqueConstraint("correction_id", "document_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correction_id: Mapped[int] = mapped_column(
        ForeignKey("answer_corrections.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def is_guest_user(user: User) -> bool:
    """访客 = guest-login 注入的内存 User：从不落库，id 恒为 None（全系统唯一判定依据）。

    刻意不用显式 flag：若未来有代码漏判访客而把 user.id 写进外键，
    会立即触发 IntegrityError 响亮失败，而不是把访客数据静默落库。
    """
    return user.id is None
