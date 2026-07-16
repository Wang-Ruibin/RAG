from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.responses import success
from app.models.enums import DocumentStatus
from app.models.orm import Conversation, Document, User
from app.rag.index import index_manager

from .dependencies import CurrentUser, Database

router = APIRouter(prefix="/api", tags=["系统"])


@router.get("/health")
def health(db: Database) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    return success(
        {
            "status": "ok",
            "database": "ok",
            "version": settings.app_version,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "indexed_chunks": index_manager.count,
        }
    )


@router.get("/stats")
def stats(db: Database, _user: CurrentUser) -> dict[str, object]:
    return success(
        {
            "documents": db.scalar(
                select(func.count(Document.id)).where(Document.status == DocumentStatus.READY)
            )
            or 0,
            "chunks": index_manager.count,
            "users": db.scalar(select(func.count(User.id))) or 0,
            "conversations": db.scalar(select(func.count(Conversation.id))) or 0,
        }
    )
