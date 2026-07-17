from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.responses import success
from app.models.orm import AnswerKnowledgeTask, Conversation, Message
from app.models.schemas import AnswerKnowledgeTaskOut, ChatRequest
from app.services.answer_knowledge import answer_knowledge_service
from app.services.chat import chat_service

from .dependencies import CurrentUser, Database

router = APIRouter(prefix="/api", tags=["问答"])


def task_dict(task: AnswerKnowledgeTask) -> dict[str, object]:
    return AnswerKnowledgeTaskOut(
        id=task.id,
        assistant_message_id=task.assistant_message_id,
        status=task.status,
        document_id=task.document_id,
        cleaned_title=task.cleaned_title,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        finished_at=task.finished_at,
    ).model_dump(mode="json")


def message_dict(message: Message, task: AnswerKnowledgeTask | None = None) -> dict[str, object]:
    return {
        "id": message.id,
        "role": message.role.value,
        "content": message.content,
        "sources": message.sources_json or [],
        "status": message.status.value,
        "model": message.model,
        "latency_ms": message.latency_ms,
        "answer_origin": message.answer_origin.value if message.answer_origin else None,
        "knowledge_task": task_dict(task) if task is not None else None,
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
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/messages/{message_id}/knowledge-task",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_answer_knowledge_task(
    message_id: int,
    db: Database,
    user: CurrentUser,
) -> dict[str, object]:
    try:
        task = answer_knowledge_service.create_task(db, user, message_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(task_dict(task), "已加入知识库处理队列", 202)


@router.get("/messages/{message_id}/knowledge-task")
def get_answer_knowledge_task_for_message(
    message_id: int,
    db: Database,
    user: CurrentUser,
) -> dict[str, object]:
    task = answer_knowledge_service.get_task_for_message(db, user, message_id)
    return success(task_dict(task) if task is not None else None)


@router.get("/knowledge-tasks/{task_id}")
def get_answer_knowledge_task(
    task_id: int,
    db: Database,
    user: CurrentUser,
) -> dict[str, object]:
    try:
        task = answer_knowledge_service.get_task(db, user, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return success(task_dict(task))


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
    task_by_message = {
        task.assistant_message_id: task
        for task in db.scalars(
            select(AnswerKnowledgeTask).where(
                AnswerKnowledgeTask.assistant_message_id.in_([message.id for message in messages])
            )
        ).all()
    }
    return success(
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                message_dict(message, task_by_message.get(message.id)) for message in messages
            ],
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
