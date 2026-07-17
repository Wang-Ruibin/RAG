from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.responses import success
from app.models.orm import Conversation, Message
from app.models.schemas import ChatRequest
from app.services.chat import chat_service

from .dependencies import CurrentUser, Database

router = APIRouter(prefix="/api", tags=["问答"])


def message_dict(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "role": message.role.value,
        "content": message.content,
        "sources": message.sources_json or [],
        "status": message.status.value,
        "model": message.model,
        "latency_ms": message.latency_ms,
        "created_at": message.created_at.isoformat(),
    }


@router.post("/chat")
def chat(body: ChatRequest, db: Database, user: CurrentUser) -> dict[str, object]:
    try:
        return success(chat_service.complete(db, user, body.question.strip(), body.conversation_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, db: Database, user: CurrentUser) -> StreamingResponse:
    try:
        conversation, assistant, history = chat_service.prepare(
            db, user, body.question.strip(), body.conversation_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        chat_service.stream(
            conversation.id,
            assistant.id,
            body.question.strip(),
            history,
            use_agent=body.use_agent,
            web_search_enabled=settings.web_search_enabled,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations")
def list_conversations(db: Database, user: CurrentUser) -> dict[str, object]:
    rows = db.execute(
        select(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    ).all()
    return success(
        [
            {
                "id": conversation.id,
                "title": conversation.title,
                "message_count": count,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            }
            for conversation, count in rows
        ]
    )


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, db: Database, user: CurrentUser) -> dict[str, object]:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id)
    ).all()
    return success(
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [message_dict(message) for message in messages],
        }
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Database, user: CurrentUser) -> dict[str, object]:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(conversation)
    db.commit()
    return success(None, "会话已删除")
