from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import (
    AnswerCorrectionStatus,
    DocumentKind,
    DocumentStatus,
    MessageRole,
    MessageStatus,
)
from app.models.orm import (
    AnswerCorrection,
    Conversation,
    CorrectionSourceLink,
    Document,
    Message,
    User,
)
from app.services.documents import DuplicateDocumentError, document_service
from app.services.message_context import previous_user_question


def utc_now() -> datetime:
    return datetime.now(UTC)


class AnswerCorrectionService:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="answer-correction")
        self._futures: set[Future[None]] = set()
        self._future_lock = threading.Lock()

    def submit_correction(
        self, db: Session, user: User, message_id: int, corrected_answer: str
    ) -> AnswerCorrection:
        message = db.get(Message, message_id)
        if message is None:
            raise LookupError("消息不存在")
        conversation = db.get(Conversation, message.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise LookupError("消息不存在")
        if message.role != MessageRole.ASSISTANT or message.status != MessageStatus.COMPLETE:
            raise ValueError("只能纠正已完成的助手回答")
        question = previous_user_question(db, message)
        if not question:
            raise ValueError("未找到对应的用户问题")

        answer = corrected_answer.strip()
        existing = db.scalar(
            select(AnswerCorrection).where(
                AnswerCorrection.assistant_message_id == message.id,
                AnswerCorrection.user_id == user.id,
            )
        )
        if existing is not None:
            if existing.status not in {
                AnswerCorrectionStatus.REJECTED,
                AnswerCorrectionStatus.FAILED,
            }:
                return existing
            existing.proposed_answer = answer
            existing.status = AnswerCorrectionStatus.PENDING
            existing.reviewed_question = None
            existing.reviewed_answer = None
            existing.reviewed_by = None
            existing.review_note = None
            existing.error = None
            existing.reviewed_at = None
            db.commit()
            db.refresh(existing)
            return existing

        correction = AnswerCorrection(
            user_id=user.id,
            conversation_id=conversation.id,
            assistant_message_id=message.id,
            contributor_name=user.name,
            contributor_email=user.email,
            original_question=question,
            original_answer=message.content,
            original_sources=list(message.sources_json or []),
            proposed_answer=answer,
            status=AnswerCorrectionStatus.PENDING,
        )
        db.add(correction)
        db.commit()
        db.refresh(correction)
        return correction

    @staticmethod
    def get_for_message(db: Session, user: User, message_id: int) -> AnswerCorrection | None:
        return db.scalar(
            select(AnswerCorrection).where(
                AnswerCorrection.assistant_message_id == message_id,
                AnswerCorrection.user_id == user.id,
            )
        )

    def approve(
        self,
        db: Session,
        admin: User,
        correction_id: int,
        *,
        question: str,
        answer: str,
        source_document_ids: list[int],
    ) -> AnswerCorrection:
        correction = db.get(AnswerCorrection, correction_id)
        if correction is None:
            raise LookupError("纠错记录不存在")
        if correction.status not in {
            AnswerCorrectionStatus.PENDING,
            AnswerCorrectionStatus.FAILED,
        }:
            raise ValueError("当前纠错状态不能批准")
        previous_document = (
            db.get(Document, correction.approved_document_id)
            if correction.approved_document_id is not None
            else None
        )
        if previous_document is not None and previous_document.status == DocumentStatus.FAILED:
            correction.approved_document_id = None
            db.commit()
            document_service.delete_document(db, previous_document)
        unique_ids = list(dict.fromkeys(source_document_ids))
        documents = (
            db.scalars(select(Document).where(Document.id.in_(unique_ids))).all()
            if unique_ids
            else []
        )
        ready_ids = {
            document.id for document in documents if document.status == DocumentStatus.READY
        }
        if ready_ids != set(unique_ids):
            raise ValueError("关联资料不存在或尚未处理完成")

        db.execute(
            delete(CorrectionSourceLink).where(CorrectionSourceLink.correction_id == correction.id)
        )
        for document_id in unique_ids:
            db.add(
                CorrectionSourceLink(
                    correction_id=correction.id,
                    document_id=document_id,
                )
            )
        correction.reviewed_question = question.strip()
        correction.reviewed_answer = answer.strip()
        correction.reviewed_by = admin.id
        correction.review_note = None
        correction.error = None
        correction.status = AnswerCorrectionStatus.PROCESSING
        correction.reviewed_at = utc_now()
        db.commit()
        db.refresh(correction)
        self.submit(correction.id)
        return correction

    @staticmethod
    def reject(db: Session, admin: User, correction_id: int, reason: str) -> AnswerCorrection:
        correction = db.get(AnswerCorrection, correction_id)
        if correction is None:
            raise LookupError("纠错记录不存在")
        if correction.status not in {
            AnswerCorrectionStatus.PENDING,
            AnswerCorrectionStatus.FAILED,
        }:
            raise ValueError("当前纠错状态不能拒绝")
        correction.status = AnswerCorrectionStatus.REJECTED
        correction.reviewed_by = admin.id
        correction.review_note = reason.strip()
        correction.error = None
        correction.reviewed_at = utc_now()
        db.commit()
        db.refresh(correction)
        return correction

    def submit(self, correction_id: int) -> None:
        future = self._executor.submit(self.process, correction_id)
        with self._future_lock:
            self._futures.add(future)
        future.add_done_callback(self._discard_future)

    def _discard_future(self, future: Future[None]) -> None:
        with self._future_lock:
            self._futures.discard(future)

    def process(self, correction_id: int) -> None:
        try:
            with SessionLocal() as db:
                correction = db.get(AnswerCorrection, correction_id)
                if correction is None or correction.status != AnswerCorrectionStatus.PROCESSING:
                    return
                question = correction.reviewed_question or correction.original_question
                answer = correction.reviewed_answer or correction.proposed_answer
                contributor_name = correction.contributor_name

            markdown = (
                f"# 用户纠错：{question[:80]}\n\n"
                f"> 内容提供者：{contributor_name}\n\n"
                "> 审核状态：管理员已审核\n\n"
                f"## 适用问题\n\n{question}\n\n"
                f"## 经审核答案\n\n{answer}\n"
            )

            with SessionLocal() as db:
                correction = db.get(AnswerCorrection, correction_id)
                if correction is None:
                    return
                try:
                    document, job = document_service.save_upload(
                        db,
                        data=markdown.encode("utf-8"),
                        original_name=f"answer-correction-{correction.id}.md",
                        mime_type="text/markdown",
                        title=f"用户纠错：{question[:80]}",
                        category=settings.answer_correction_category,
                        uploaded_by=correction.reviewed_by or correction.user_id,
                        enqueue=False,
                        document_kind=DocumentKind.USER_CORRECTION,
                        contributor_name=contributor_name,
                    )
                    document_id = document.id
                    job_id = job.id
                except DuplicateDocumentError as exc:
                    existing = db.get(Document, exc.document_id)
                    if existing is None or existing.status != DocumentStatus.READY:
                        raise
                    document_id = existing.id
                    job_id = None
                correction.approved_document_id = document_id
                db.commit()

            if job_id is not None:
                document_service.process(document_id, job_id, rebuild=True)
            with SessionLocal() as db:
                document = db.get(Document, document_id)
                correction = db.get(AnswerCorrection, correction_id)
                if correction is None:
                    return
                if document is None or document.status != DocumentStatus.READY:
                    reason = document.error if document is not None else "知识文档不存在"
                    raise RuntimeError(reason or "纠错知识文档处理失败")
                correction.status = AnswerCorrectionStatus.APPROVED
                correction.error = None
                db.commit()
        except Exception as exc:
            with SessionLocal() as db:
                correction = db.get(AnswerCorrection, correction_id)
                if correction is not None:
                    correction.status = AnswerCorrectionStatus.FAILED
                    correction.error = f"{type(exc).__name__}: {exc}"[:4000]
                    db.commit()

    @staticmethod
    def recover_stuck_corrections() -> int:
        """Resolve approvals interrupted between document ingestion and the final status write."""
        with SessionLocal() as db:
            corrections = db.scalars(
                select(AnswerCorrection).where(
                    AnswerCorrection.status == AnswerCorrectionStatus.PROCESSING
                )
            ).all()
            for correction in corrections:
                document = (
                    db.get(Document, correction.approved_document_id)
                    if correction.approved_document_id is not None
                    else None
                )
                if document is not None and document.status == DocumentStatus.READY:
                    correction.status = AnswerCorrectionStatus.APPROVED
                    correction.error = None
                else:
                    correction.status = AnswerCorrectionStatus.FAILED
                    correction.error = "服务重启中断了纠错入库，请管理员重新批准"
            db.commit()
            return len(corrections)


answer_correction_service = AnswerCorrectionService()
