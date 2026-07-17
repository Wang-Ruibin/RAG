from __future__ import annotations

import re
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import (
    AnswerKnowledgeStatus,
    AnswerOrigin,
    DocumentStatus,
    MessageRole,
    MessageStatus,
)
from app.models.orm import AnswerKnowledgeTask, Conversation, Document, Message, User
from app.rag.generation import generator
from app.services.documents import DuplicateDocumentError, document_service


def utc_now() -> datetime:
    return datetime.now(UTC)


class AnswerKnowledgeService:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="answer-knowledge")
        self._futures: set[Future[None]] = set()
        self._future_lock = threading.Lock()

    def create_task(
        self,
        db: Session,
        user: User,
        assistant_message_id: int,
    ) -> AnswerKnowledgeTask:
        message = db.get(Message, assistant_message_id)
        if message is None:
            raise LookupError("消息不存在")
        conversation = db.get(Conversation, message.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise LookupError("消息不存在")
        if message.role != MessageRole.ASSISTANT or message.status != MessageStatus.COMPLETE:
            raise ValueError("只能沉淀已完成的助手回答")
        if not message.content.strip():
            raise ValueError("空回答不能加入知识库")
        if message.answer_origin == AnswerOrigin.NO_ANSWER:
            raise ValueError("无答案回复不能加入知识库")

        existing = db.scalar(
            select(AnswerKnowledgeTask).where(
                AnswerKnowledgeTask.assistant_message_id == assistant_message_id
            )
        )
        if existing is not None:
            return existing

        question = self._previous_user_question(db, message)
        if not question:
            raise ValueError("未找到对应的用户问题")

        task = AnswerKnowledgeTask(
            user_id=user.id,
            conversation_id=conversation.id,
            assistant_message_id=message.id,
            source_answer_origin=message.answer_origin,
            original_question=question[:1000],
            original_answer=message.content[: settings.answer_knowledge_max_answer_chars],
            sources_snapshot=self._source_snapshot(message.sources_json or []),
            status=AnswerKnowledgeStatus.QUEUED,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        self.submit(task.id)
        return task

    def get_task_for_message(
        self, db: Session, user: User, assistant_message_id: int
    ) -> AnswerKnowledgeTask | None:
        task = db.scalar(
            select(AnswerKnowledgeTask).where(
                AnswerKnowledgeTask.assistant_message_id == assistant_message_id,
                AnswerKnowledgeTask.user_id == user.id,
            )
        )
        return task

    def get_task(self, db: Session, user: User, task_id: int) -> AnswerKnowledgeTask:
        task = db.scalar(
            select(AnswerKnowledgeTask).where(
                AnswerKnowledgeTask.id == task_id,
                AnswerKnowledgeTask.user_id == user.id,
            )
        )
        if task is None:
            raise LookupError("任务不存在")
        return task

    def submit(self, task_id: int) -> None:
        future = self._executor.submit(self.process, task_id)
        with self._future_lock:
            self._futures.add(future)
        future.add_done_callback(self._discard_future)

    def _discard_future(self, future: Future[None]) -> None:
        with self._future_lock:
            self._futures.discard(future)

    def process(self, task_id: int) -> None:
        self._set_status(task_id, AnswerKnowledgeStatus.PROCESSING, start=True)
        try:
            with SessionLocal() as db:
                task = db.get(AnswerKnowledgeTask, task_id)
                if task is None:
                    return
                question = task.original_question
                answer = task.original_answer
                sources = task.sources_snapshot or []

            cleaned = generator.clean_answer_for_knowledge(
                question=question,
                answer=answer,
                sources=sources,
            )
            title, markdown = self._normalize_markdown(question, cleaned)
            data = markdown.encode("utf-8")

            with SessionLocal() as db:
                task = db.get(AnswerKnowledgeTask, task_id)
                if task is None:
                    return
                task.cleaned_title = title
                task.cleaned_content = markdown
                db.commit()

                try:
                    document, job = document_service.save_upload(
                        db,
                        data=data,
                        original_name=f"answer-{task.assistant_message_id}.md",
                        mime_type="text/markdown",
                        title=title,
                        category=settings.answer_knowledge_category,
                        uploaded_by=task.user_id,
                        enqueue=False,
                    )
                except DuplicateDocumentError as exc:
                    task.document_id = exc.document_id
                    task.status = AnswerKnowledgeStatus.COMPLETE
                    task.error = None
                    task.finished_at = utc_now()
                    db.commit()
                    return

                task.document_id = document.id
                db.commit()
                document_id = document.id
                job_id = job.id

            document_service.process(document_id, job_id, rebuild=True)
            with SessionLocal() as db:
                task = db.get(AnswerKnowledgeTask, task_id)
                document = db.get(Document, document_id)
                if task is None:
                    return
                if document is None or document.status != DocumentStatus.READY:
                    reason = document.error if document is not None else "文档不存在"
                    raise RuntimeError(reason or "知识库入库失败")
                task.status = AnswerKnowledgeStatus.COMPLETE
                task.error = None
                task.finished_at = utc_now()
                db.commit()
        except Exception as exc:
            self._fail(task_id, exc)

    @staticmethod
    def _previous_user_question(db: Session, assistant: Message) -> str:
        previous = db.scalar(
            select(Message)
            .where(
                Message.conversation_id == assistant.conversation_id,
                Message.id < assistant.id,
                Message.role == MessageRole.USER,
            )
            .order_by(Message.id.desc())
        )
        return previous.content.strip() if previous is not None else ""

    @staticmethod
    def _source_snapshot(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        budget = settings.answer_knowledge_max_source_chars
        for source in sources[:8]:
            item = {
                key: source.get(key)
                for key in (
                    "source_type",
                    "citation_index",
                    "title",
                    "url",
                    "source_url",
                    "site_name",
                    "domain",
                    "published_at",
                    "snippet",
                    "content",
                )
                if source.get(key) not in (None, "")
            }
            text_size = sum(len(str(value)) for value in item.values())
            if text_size > budget:
                item["snippet"] = str(item.get("snippet") or "")[: max(0, budget)]
                item.pop("content", None)
                text_size = sum(len(str(value)) for value in item.values())
            if budget - text_size < 0:
                break
            budget -= text_size
            kept.append(item)
        return kept

    @staticmethod
    def _normalize_markdown(question: str, cleaned: str) -> tuple[str, str]:
        markdown = cleaned.strip()
        markdown = re.sub(r"^```(?:markdown)?\s*", "", markdown, flags=re.I)
        markdown = re.sub(r"\s*```$", "", markdown).strip()
        if not markdown or markdown.startswith("无法整理"):
            raise ValueError("清洗后的内容不足，未写入知识库")
        title_match = re.search(r"^#\s+(.+)$", markdown, flags=re.M)
        title = title_match.group(1).strip() if title_match else question.strip()
        title = re.sub(r"\s+", " ", title)[:80] or "问答沉淀"
        if not title_match:
            markdown = f"# {title}\n\n{markdown}"
        markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
        if len(re.sub(r"[#*\s`>-]", "", markdown)) < 30:
            raise ValueError("清洗后的内容过短，未写入知识库")
        return title, markdown

    def _set_status(
        self,
        task_id: int,
        status: AnswerKnowledgeStatus,
        *,
        start: bool = False,
    ) -> None:
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if task is None:
                return
            task.status = status
            task.error = None
            if start:
                task.started_at = utc_now()
            db.commit()

    def _fail(self, task_id: int, exc: Exception) -> None:
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if task is None:
                return
            task.status = AnswerKnowledgeStatus.FAILED
            task.error = f"{type(exc).__name__}: {exc}"[:4000]
            task.finished_at = utc_now()
            db.commit()


answer_knowledge_service = AnswerKnowledgeService()
