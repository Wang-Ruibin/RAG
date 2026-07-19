from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.responses import success
from app.models.enums import AnswerCorrectionStatus, AnswerOrigin, MessageRole, MessageStatus
from app.models.orm import AnswerCorrection, Conversation, CorrectionSourceLink, Message, User
from app.models.schemas import (
    AnswerCorrectionApproveRequest,
    AnswerCorrectionRejectRequest,
    UserOut,
    UserUpdateRequest,
)
from app.services.answer_corrections import answer_correction_service

from .chat import correction_dict
from .dependencies import CurrentUser, Database

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/users")
def list_users(
    db: Database,
    _user: CurrentUser,
) -> dict[str, object]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return success([UserOut.model_validate(user).model_dump(mode="json") for user in users])


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Database,
    editor: CurrentUser,
) -> dict[str, object]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == editor.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前管理员")
    if user.id == editor.id and body.role is not None and body.role != editor.role:
        raise HTTPException(status_code=400, detail="不能降低当前管理员角色")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(mode="json"), "用户已更新")


@router.get("/qa-conversations")
def list_qa_conversations(
    db: Database,
    _user: CurrentUser,
    keyword: str | None = Query(None, max_length=200, description="搜索关键词（问题/答案/标题）"),
    user_id: int | None = Query(None, description="按用户ID筛选"),
    user_name: str | None = Query(None, max_length=200, description="按用户名模糊搜索"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    answer_origin: AnswerOrigin | None = Query(None, description="来源类型"),
    status: MessageStatus | None = Query(None, description="消息状态"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> dict[str, object]:
    """管理员查看全量问答记录，支持多条件筛选与分页。"""
    page = max(1, page)
    size = min(max(1, size), 100)

    # 标量子查询：每个对话的第一条用户消息（问题）
    first_question = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.USER)
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    # 第一条助手消息（答案、来源、状态）
    first_answer = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.ASSISTANT)
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    first_sources = (
        select(Message.sources_json)
        .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.ASSISTANT)
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    first_answer_origin = (
        select(Message.answer_origin)
        .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.ASSISTANT)
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    first_answer_status = (
        select(Message.status)
        .where(Message.conversation_id == Conversation.id, Message.role == MessageRole.ASSISTANT)
        .order_by(Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )

    cols = [
        Conversation.id.label("conversation_id"),
        Conversation.title.label("conversation_title"),
        Conversation.created_at,
        User.id.label("user_id"),
        User.name.label("user_name"),
        first_question.label("question"),
        first_answer.label("answer"),
        first_sources.label("sources"),
        first_answer_origin.label("answer_origin"),
        first_answer_status.label("status"),
    ]

    base = select(*cols).select_from(Conversation).join(User, Conversation.user_id == User.id)

    filters: list = []
    if keyword:
        kw = keyword.strip()
        # 搜索对话标题
        title_match = Conversation.title.contains(kw, autoescape=True)
        # 搜索消息内容
        msg_match = (
            select(Message.id)
            .where(Message.conversation_id == Conversation.id)
            .where(Message.content.contains(kw, autoescape=True))
            .correlate(Conversation)
            .exists()
        )
        filters.append(title_match | msg_match)
    if user_id is not None:
        filters.append(Conversation.user_id == user_id)
    if user_name and user_name.strip():
        filters.append(User.name.contains(user_name.strip(), autoescape=True))
    if start_date is not None:
        filters.append(func.date(Conversation.created_at) >= start_date)
    if end_date is not None:
        filters.append(func.date(Conversation.created_at) <= end_date)
    if answer_origin is not None:
        filters.append(
            select(Message.id)
            .where(Message.conversation_id == Conversation.id)
            .where(Message.role == MessageRole.ASSISTANT)
            .where(Message.answer_origin == answer_origin)
            .correlate(Conversation)
            .exists()
        )
    if status is not None:
        filters.append(
            select(Message.id)
            .where(Message.conversation_id == Conversation.id)
            .where(Message.role == MessageRole.ASSISTANT)
            .where(Message.status == status)
            .correlate(Conversation)
            .exists()
        )

    base = base.where(*filters)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    rows = db.execute(
        base.order_by(Conversation.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items = [
        {
            "conversation_id": row.conversation_id,
            "conversation_title": row.conversation_title,
            "question": row.question or "",
            "answer": row.answer or "",
            "sources": row.sources or [],
            "user_id": row.user_id,
            "user_name": row.user_name,
            "answer_origin": row.answer_origin.value if row.answer_origin else None,
            "status": row.status.value if row.status else None,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]

    return success({"items": items, "total": total, "page": page, "size": size})


@router.delete("/qa-conversations/{conversation_id}")
def delete_qa_conversation(
    conversation_id: int,
    db: Database,
    _user: CurrentUser,
) -> dict[str, object]:
    """管理员删除任意问答会话（含级联删除消息）。"""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(conversation)
    db.commit()
    return success(None, "会话已删除")


def admin_correction_dict(db: Database, correction: AnswerCorrection) -> dict[str, object]:
    payload = correction_dict(correction)
    payload.update(
        {
            "user_id": correction.user_id,
            "contributor_name": correction.contributor_name,
            "contributor_email": correction.contributor_email,
            "original_question": correction.original_question,
            "original_answer": correction.original_answer,
            "original_sources": correction.original_sources or [],
            "source_document_ids": list(
                db.scalars(
                    select(CorrectionSourceLink.document_id).where(
                        CorrectionSourceLink.correction_id == correction.id
                    )
                ).all()
            ),
        }
    )
    return payload


@router.get("/answer-corrections")
def list_answer_corrections(
    db: Database,
    _user: CurrentUser,
    page: int = 1,
    size: int = 20,
    status_filter: AnswerCorrectionStatus | None = None,
) -> dict[str, object]:
    page = max(1, page)
    size = min(max(1, size), 100)
    filters = [AnswerCorrection.status == status_filter] if status_filter else []
    total = db.scalar(select(func.count(AnswerCorrection.id)).where(*filters)) or 0
    corrections = db.scalars(
        select(AnswerCorrection)
        .where(*filters)
        .order_by(AnswerCorrection.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return success(
        {
            "items": [admin_correction_dict(db, item) for item in corrections],
            "total": total,
            "page": page,
            "size": size,
        }
    )


@router.post(
    "/answer-corrections/{correction_id}/approve",
    status_code=status.HTTP_202_ACCEPTED,
)
def approve_answer_correction(
    correction_id: int,
    body: AnswerCorrectionApproveRequest,
    db: Database,
    reviewer: CurrentUser,
) -> dict[str, object]:
    try:
        correction = answer_correction_service.approve(
            db,
            reviewer,
            correction_id,
            question=body.question,
            answer=body.answer,
            source_document_ids=body.source_document_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(admin_correction_dict(db, correction), "已批准，正在生成知识文档", 202)


@router.post("/answer-corrections/{correction_id}/reject")
def reject_answer_correction(
    correction_id: int,
    body: AnswerCorrectionRejectRequest,
    db: Database,
    reviewer: CurrentUser,
) -> dict[str, object]:
    try:
        correction = answer_correction_service.reject(db, reviewer, correction_id, body.reason)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(admin_correction_dict(db, correction), "纠错已拒绝")
