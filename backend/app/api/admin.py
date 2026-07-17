from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.responses import success
from app.models.enums import AnswerCorrectionStatus
from app.models.orm import AnswerCorrection, CorrectionSourceLink, User
from app.models.schemas import (
    AnswerCorrectionApproveRequest,
    AnswerCorrectionRejectRequest,
    UserOut,
    UserUpdateRequest,
)
from app.services.answer_corrections import answer_correction_service

from .chat import correction_dict
from .dependencies import AdminUser, Database

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/users")
def list_users(db: Database, _admin: AdminUser) -> dict[str, object]:
    users = db.scalars(select(User).order_by(User.created_at.desc())).all()
    return success([UserOut.model_validate(user).model_dump(mode="json") for user in users])


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Database,
    admin: AdminUser,
) -> dict[str, object]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前管理员")
    if user.id == admin.id and body.role is not None and body.role != admin.role:
        raise HTTPException(status_code=400, detail="不能降低当前管理员角色")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(mode="json"), "用户已更新")


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
    _admin: AdminUser,
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
    admin: AdminUser,
) -> dict[str, object]:
    try:
        correction = answer_correction_service.approve(
            db,
            admin,
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
    admin: AdminUser,
) -> dict[str, object]:
    try:
        correction = answer_correction_service.reject(db, admin, correction_id, body.reason)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(admin_correction_dict(db, correction), "纠错已拒绝")
