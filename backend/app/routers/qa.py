"""问答记录 API 路由"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.cache.qa_cache import QACache
from app.database import get_db
from app.schemas.qa_record import AnswerCreate, QARecordCreate, QARecordResponse
from app.services.qa_service import QAService
from app.routers.user import _get_current_user

router = APIRouter(prefix="/api/qa", tags=["问答记录"])


def _success(data=None, message="success"):
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


@router.post("/ask")
def ask_question(
    question: str = Query(..., description="用户问题"),
    session_id: str | None = Query(None, description="会话ID"),
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """
    提交问题

    先查缓存，缓存命中直接返回缓存结果；
    缓存未命中时，返回问题信息（由上游RAG引擎生成回答后回填）。
    """
    # 1. 查缓存
    cached = QACache.get_cached_answer(user_id, question)
    if cached:
        # 缓存命中，仅记录到会话历史
        if session_id:
            QACache.append_to_session(session_id, question, cached)
        QACache.increment_hot_count(question)
        return _success(
            data={
                "question": question,
                "answer": cached,
                "from_cache": True,
                "session_id": session_id,
            },
            message="缓存命中",
        )

    # 2. 缓存未命中，创建记录（answer 为空，由后续 RAG 引擎填充）
    record = QAService.create(
        db,
        QARecordCreate(
            user_id=user_id,
            session_id=session_id,
            question=question,
        ),
    )

    # 记录到会话缓存
    if session_id:
        QACache.append_to_session(session_id, question, "")

    QACache.increment_hot_count(question)

    return _success(
        data=QARecordResponse.model_validate(record).model_dump(),
        message="问题已提交，等待回答",
    )


@router.post("/answer")
def save_answer(
    data: AnswerCreate,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """保存AI回答并写入缓存"""
    record = QAService.get_by_id(db, data.record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权限修改此记录")

    # 更新回答
    record.answer = data.answer
    if data.sources is not None:
        record.sources = data.sources
    record.tokens_used = data.tokens_used
    if data.duration_ms is not None:
        record.duration_ms = data.duration_ms
    db.commit()
    db.refresh(record)

    # 写入缓存
    QACache.set_cached_answer(user_id, record.question, data.answer)

    # 更新会话缓存
    if record.session_id:
        # 删除最后一条空回答，重新追加
        QACache.clear_session(record.session_id)
        # 重新加载该会话的所有记录到缓存
        records, _ = QAService.get_session_history(db, record.session_id, page_size=100)
        for r in records:
            if r.answer:
                QACache.append_to_session(record.session_id, r.question, r.answer)

    return _success(
        data=QARecordResponse.model_validate(record).model_dump(),
        message="回答已保存",
    )


@router.get("/history")
def get_history(
    page: int = 1,
    page_size: int = 20,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """获取会话列表（按session_id分组）"""
    sessions, total = QAService.get_user_sessions(
        db, user_id, page=page, page_size=page_size
    )
    return _success(
        data={
            "total": total,
            "items": sessions,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/session/{session_id}")
def get_session_detail(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """获取单会话详情"""
    records, total = QAService.get_session_history(
        db, session_id, page=page, page_size=page_size
    )
    return _success(
        data={
            "total": total,
            "items": [QARecordResponse.model_validate(r).model_dump() for r in records],
            "page": page,
            "page_size": page_size,
            "session_id": session_id,
        }
    )


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """删除会话"""
    deleted = QAService.delete_session(db, session_id, user_id=user_id)
    # 清除缓存
    QACache.clear_session(session_id)
    return _success(
        data={"deleted_count": deleted},
        message="会话已删除",
    )


@router.get("/hot")
def get_hot_questions(limit: int = 10):
    """获取热门问题"""
    questions = QACache.get_hot_questions(limit=limit)
    return _success(data={"questions": questions})


@router.post("/feedback")
def submit_feedback(
    record_id: int = Query(..., description="记录ID"),
    feedback: int = Query(..., description="反馈: 1=有用, 2=无用"),
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """提交问答反馈"""
    try:
        record = QAService.update_feedback(db, record_id, feedback)
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        return _success(message="反馈已提交")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
