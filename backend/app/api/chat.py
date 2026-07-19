from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.responses import success
from app.models.orm import AnswerCorrection, AnswerKnowledgeTask, Conversation, Message
from app.models.schemas import (
    AnswerCorrectionOut,
    AnswerCorrectionSubmitRequest,
    AnswerKnowledgeTaskOut,
    ChatRequest,
    ConversationRenameRequest,
)
from app.services.answer_corrections import answer_correction_service
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
        qa_entry_id=task.qa_entry_id,
        cleaned_title=task.cleaned_title,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        finished_at=task.finished_at,
    ).model_dump(mode="json")


def correction_dict(correction: AnswerCorrection) -> dict[str, object]:
    return AnswerCorrectionOut(
        id=correction.id,
        assistant_message_id=correction.assistant_message_id,
        status=correction.status,
        proposed_answer=correction.proposed_answer,
        reviewed_question=correction.reviewed_question,
        reviewed_answer=correction.reviewed_answer,
        review_note=correction.review_note,
        approved_document_id=correction.approved_document_id,
        error=correction.error,
        created_at=correction.created_at,
        updated_at=correction.updated_at,
        reviewed_at=correction.reviewed_at,
    ).model_dump(mode="json")


def message_dict(
    message: Message,
    task: AnswerKnowledgeTask | None = None,
    correction: AnswerCorrection | None = None,
) -> dict[str, object]:
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
        "correction": correction_dict(correction) if correction is not None else None,
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


@router.post("/messages/{message_id}/correction", status_code=status.HTTP_202_ACCEPTED)
def submit_answer_correction(
    message_id: int,
    body: AnswerCorrectionSubmitRequest,
    db: Database,
    user: CurrentUser,
) -> dict[str, object]:
    try:
        correction = answer_correction_service.submit_correction(
            db, user, message_id, body.corrected_answer
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(correction_dict(correction), "纠错已提交，等待管理员审核", 202)


@router.get("/conversations")
def list_conversations(
    db: Database,
    user: CurrentUser,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> dict[str, object]:
    statement = (
        select(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    query = (q or "").strip()
    if query:
        statement = statement.where(Conversation.title.contains(query, autoescape=True))
    rows = db.execute(statement).all()
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


@router.patch("/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: int,
    body: ConversationRenameRequest,
    db: Database,
    user: CurrentUser,
) -> dict[str, object]:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation.title = body.title
    db.commit()
    db.refresh(conversation)
    return success(
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        },
        "会话已重命名",
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
    correction_by_message = {
        correction.assistant_message_id: correction
        for correction in db.scalars(
            select(AnswerCorrection).where(
                AnswerCorrection.assistant_message_id.in_([message.id for message in messages])
            )
        ).all()
        if correction.assistant_message_id is not None
    }
    return success(
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                message_dict(
                    message,
                    task_by_message.get(message.id),
                    correction_by_message.get(message.id),
                )
                for message in messages
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
