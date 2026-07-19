from __future__ import annotations

import hashlib
import re
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import (
    AnswerKnowledgeStatus,
    AnswerOrigin,
    DocumentKind,
    DocumentStatus,
    MessageRole,
    MessageStatus,
)
from app.models.orm import (
    AnswerKnowledgeTask,
    Conversation,
    Document,
    Message,
    QaEntry,
    QaSourceLink,
    User,
)
from app.rag import embedding
from app.rag.generation import generator
from app.rag.index import index_manager
from app.rag.qa_index import qa_index_manager
from app.services.documents import DuplicateDocumentError, document_service
from app.services.message_context import previous_user_question
from app.services.qa_knowledge import normalize_question, question_hash


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SourceLinkDraft:
    document_id: int
    chunk_id: int | None
    marker: str
    citation_index: int
    source_kind: str


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

        question = previous_user_question(db, message)
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
        return db.scalar(
            select(AnswerKnowledgeTask).where(
                AnswerKnowledgeTask.assistant_message_id == assistant_message_id,
                AnswerKnowledgeTask.user_id == user.id,
            )
        )

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
                message = db.get(Message, task.assistant_message_id)
                question = task.original_question.strip()
                answer = task.original_answer.strip()
                sources = (
                    list(message.sources_json or [])
                    if message is not None
                    else list(task.sources_snapshot or [])
                )
                user_id = task.user_id
                source_origin = task.source_answer_origin
                existing_cleaned = task.cleaned_content

            selected_sources = self._cited_sources(answer, sources)
            link_drafts = self._materialize_sources(selected_sources, user_id)
            if not link_drafts:
                raise ValueError("回答没有可用的引用来源，未加入知识库")

            vector = embedding.embedder.embed_query(question)
            duplicate = self._find_duplicate(question, vector)
            if duplicate is not None:
                self._merge_links(duplicate.id, link_drafts)
                match = qa_index_manager.get(duplicate.id)
                self._complete_task(
                    task_id,
                    qa_entry_id=duplicate.id,
                    title=match.title if match else "问答知识",
                    cleaned_content=match.answer if match else None,
                )
                return

            cleaned = existing_cleaned or generator.clean_answer_for_knowledge(
                question=question,
                answer=answer,
                sources=selected_sources,
            )
            title, canonical_question, canonical_answer = self._normalize_qa(
                question, cleaned, link_drafts
            )
            digest = hashlib.sha256(
                f"{normalize_question(canonical_question)}\n{canonical_answer}".encode()
            ).hexdigest()

            with SessionLocal() as db:
                canonical_duplicate = db.scalar(
                    select(QaEntry).where(
                        QaEntry.question_hash == question_hash(canonical_question),
                        QaEntry.is_active.is_(True),
                    )
                )
                if canonical_duplicate is not None:
                    duplicate_id = canonical_duplicate.id
                else:
                    duplicate_id = None
            if duplicate_id is not None:
                match = qa_index_manager.get(duplicate_id)
                if match is None:
                    qa_index_manager.upsert(
                        entry_id=duplicate_id,
                        title=title,
                        question=canonical_question,
                        answer=canonical_answer,
                        vector=vector,
                    )
                    match = qa_index_manager.get(duplicate_id)
                self._merge_links(duplicate_id, link_drafts)
                self._complete_task(
                    task_id,
                    qa_entry_id=duplicate_id,
                    title=match.title if match else title,
                    cleaned_content=match.answer if match else canonical_answer,
                )
                return

            with SessionLocal() as db:
                entry = QaEntry(
                    created_by=user_id,
                    question_hash=question_hash(canonical_question),
                    content_hash=digest,
                    source_answer_origin=source_origin,
                    is_active=True,
                )
                db.add(entry)
                db.commit()
                db.refresh(entry)
                entry_id = entry.id

            try:
                qa_index_manager.upsert(
                    entry_id=entry_id,
                    title=title,
                    question=canonical_question,
                    answer=canonical_answer,
                    vector=vector,
                )
                self._merge_links(entry_id, link_drafts)
            except Exception:
                qa_index_manager.delete(entry_id)
                with SessionLocal() as db:
                    entry = db.get(QaEntry, entry_id)
                    if entry is not None:
                        db.delete(entry)
                        db.commit()
                raise

            self._complete_task(
                task_id,
                qa_entry_id=entry_id,
                title=title,
                cleaned_content=canonical_answer,
            )
        except Exception as exc:
            self._fail(task_id, exc)

    def migrate_legacy_task(self, task_id: int) -> bool:
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if task is None or task.qa_entry_id is not None:
                return False
            legacy_document_id = task.document_id
            task.status = AnswerKnowledgeStatus.QUEUED
            task.error = None
            db.commit()
        self.process(task_id)
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if (
                task is None
                or task.status != AnswerKnowledgeStatus.COMPLETE
                or task.qa_entry_id is None
            ):
                return False
            if legacy_document_id is not None:
                legacy_document = db.get(Document, legacy_document_id)
                if legacy_document is not None:
                    document_service.delete_document(db, legacy_document)
                task = db.get(AnswerKnowledgeTask, task_id)
                if task is not None:
                    task.document_id = None
                    db.commit()
            return True

    def _find_duplicate(self, question: str, vector) -> QaEntry | None:  # type: ignore[no-untyped-def]
        digest = question_hash(question)
        with SessionLocal() as db:
            exact = db.scalar(
                select(QaEntry).where(
                    QaEntry.question_hash == digest,
                    QaEntry.is_active.is_(True),
                )
            )
            if exact is not None and qa_index_manager.get(exact.id) is not None:
                return exact

        matches = qa_index_manager.search(vector, 1)
        if not matches or matches[0].score < settings.qa_dedupe_min_score:
            return None
        with SessionLocal() as db:
            entry = db.get(QaEntry, matches[0].entry_id)
            if entry is None or not entry.is_active:
                return None
            db.expunge(entry)
            return entry

    def _materialize_sources(
        self, sources: list[dict[str, Any]], user_id: int
    ) -> list[SourceLinkDraft]:
        drafts: list[SourceLinkDraft] = []
        rebuilt = False
        for position, source in enumerate(sources[: settings.context_top_k], start=1):
            marker = self._source_marker(source)
            citation_index = int(source.get("citation_index") or position)
            if marker == "S":
                document_id = int(source.get("document_id") or 0)
                if not document_id:
                    continue
                with SessionLocal() as db:
                    document = db.get(Document, document_id)
                    if document is None or document.status != DocumentStatus.READY:
                        continue
                drafts.append(
                    SourceLinkDraft(
                        document_id=document_id,
                        chunk_id=int(source.get("chunk_id") or 0) or None,
                        marker="S",
                        citation_index=citation_index,
                        source_kind=(
                            "WEB_ARCHIVE"
                            if source.get("source_type") == "WEB_ARCHIVE"
                            else "KNOWLEDGE_BASE"
                        ),
                    )
                )
                continue

            document_id, created = self._archive_web_source(source, user_id)
            rebuilt = rebuilt or created
            drafts.append(
                SourceLinkDraft(
                    document_id=document_id,
                    chunk_id=index_manager.stable_chunk_id(document_id, 0),
                    marker="W",
                    citation_index=citation_index,
                    source_kind="WEB_ARCHIVE",
                )
            )
        if rebuilt:
            index_manager.rebuild()
        return self._deduplicate_link_drafts(drafts)

    def _archive_web_source(self, source: dict[str, Any], user_id: int) -> tuple[int, bool]:
        url = self._normalize_url(str(source.get("url") or source.get("source_url") or ""))
        if not url:
            raise ValueError("网页来源缺少有效 URL")
        with SessionLocal() as db:
            existing = db.scalar(
                select(Document).where(
                    Document.source_url == url,
                    Document.status != DocumentStatus.DELETING,
                )
            )
            if existing is not None:
                if existing.status != DocumentStatus.READY:
                    raise ValueError(f"网页归档尚未就绪: {url}")
                return existing.id, False

        title = str(source.get("title") or urlparse(url).netloc or "网页来源").strip()[:300]
        content = str(source.get("content") or source.get("snippet") or "").strip()
        if not content:
            raise ValueError(f"网页来源没有可归档内容: {url}")
        published_at = self._parse_date(source.get("published_at"))
        date_line = published_at.isoformat() if published_at else "未知"
        markdown = (
            f"# {title}\n\n"
            f"来源链接：{url}\n\n"
            f"发布日期：{date_line}\n\n"
            f"## 网页内容快照\n\n{content}\n"
        )
        data = markdown.encode("utf-8")
        with SessionLocal() as db:
            try:
                document, job = document_service.save_upload(
                    db,
                    data=data,
                    original_name=f"web-{hashlib.sha256(url.encode()).hexdigest()[:16]}.md",
                    mime_type="text/markdown",
                    title=title,
                    category=settings.answer_web_archive_category,
                    uploaded_by=user_id,
                    enqueue=False,
                    document_kind=DocumentKind.WEB_ARCHIVE,
                )
            except DuplicateDocumentError as exc:
                duplicate = db.get(Document, exc.document_id)
                if duplicate is None or duplicate.status != DocumentStatus.READY:
                    raise
                return duplicate.id, False
            document.source_url = url
            document.published_at = published_at
            db.commit()
            document_id = document.id
            job_id = job.id
        document_service.process(document_id, job_id, rebuild=False)
        with SessionLocal() as db:
            document = db.get(Document, document_id)
            if document is None or document.status != DocumentStatus.READY:
                reason = document.error if document is not None else "文档不存在"
                raise RuntimeError(reason or "网页来源归档失败")
        return document_id, True

    @staticmethod
    def _merge_links(entry_id: int, drafts: list[SourceLinkDraft]) -> None:
        with SessionLocal() as db:
            existing_document_ids = set(
                db.scalars(
                    select(QaSourceLink.document_id).where(QaSourceLink.qa_entry_id == entry_id)
                ).all()
            )
            for draft in drafts:
                if draft.document_id in existing_document_ids:
                    continue
                db.add(
                    QaSourceLink(
                        qa_entry_id=entry_id,
                        document_id=draft.document_id,
                        source_chunk_id=draft.chunk_id,
                        marker=draft.marker,
                        citation_index=draft.citation_index,
                        source_kind=draft.source_kind,
                    )
                )
                existing_document_ids.add(draft.document_id)
            db.commit()

    @staticmethod
    def _cited_sources(answer: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cited = {(marker, int(index)) for marker, index in re.findall(r"\[([SW])(\d+)\]", answer)}
        if not cited:
            return sources[: settings.context_top_k]
        selected = []
        for position, source in enumerate(sources, start=1):
            marker = AnswerKnowledgeService._source_marker(source)
            citation_index = int(source.get("citation_index") or position)
            if (marker, citation_index) in cited:
                selected.append(source)
        return selected[: settings.context_top_k]

    @staticmethod
    def _source_marker(source: dict[str, Any]) -> str:
        return "W" if source.get("source_type") == "WEB_SEARCH" else "S"

    @staticmethod
    def _deduplicate_link_drafts(drafts: list[SourceLinkDraft]) -> list[SourceLinkDraft]:
        kept: list[SourceLinkDraft] = []
        seen: set[int] = set()
        for draft in drafts:
            if draft.document_id in seen:
                continue
            seen.add(draft.document_id)
            kept.append(draft)
        return kept

    @staticmethod
    def _normalize_qa(
        question: str,
        cleaned: str,
        sources: list[SourceLinkDraft],
    ) -> tuple[str, str, str]:
        markdown = cleaned.strip()
        markdown = re.sub(r"^```(?:markdown)?\s*", "", markdown, flags=re.I)
        markdown = re.sub(r"\s*```$", "", markdown).strip()
        if not markdown or markdown.startswith("无法整理"):
            raise ValueError("清洗后的内容不足，未写入知识库")
        title_match = re.search(r"^#\s+(.+)$", markdown, flags=re.M)
        title = title_match.group(1).strip() if title_match else question.strip()
        title = re.sub(r"\s+", " ", title)[:80] or "问答知识"
        question_match = re.search(
            r"^##\s+(?:标准问题|适用问题)\s*\n(.+?)(?=^##\s+|\Z)",
            markdown,
            flags=re.M | re.S,
        )
        answer_match = re.search(
            r"^##\s+(?:标准答案|知识条目)\s*\n(.+?)(?=^##\s+|\Z)",
            markdown,
            flags=re.M | re.S,
        )
        canonical_question = (
            re.sub(r"\s+", " ", question_match.group(1)).strip()
            if question_match
            else question.strip()
        )
        canonical_answer = answer_match.group(1).strip() if answer_match else markdown
        canonical_answer = re.sub(r"\n{3,}", "\n\n", canonical_answer).strip()
        if len(re.sub(r"[#*\s`>-]", "", canonical_answer)) < 20:
            raise ValueError("清洗后的答案过短，未写入知识库")
        references = re.findall(r"\[([SW])(\d+)\]", canonical_answer)
        if not references:
            suffix = " ".join(f"[{item.marker}{item.citation_index}]" for item in sources)
            canonical_answer = f"{canonical_answer}\n\n来源：{suffix}".strip()
        return title, canonical_question[:1000], canonical_answer

    @staticmethod
    def _normalize_url(value: str) -> str | None:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path or "/",
                "",
                parsed.query,
                "",
            )
        )

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

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
                    "chunk_id",
                    "document_id",
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
    def _complete_task(
        task_id: int,
        *,
        qa_entry_id: int,
        title: str,
        cleaned_content: str | None,
    ) -> None:
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if task is None:
                return
            task.qa_entry_id = qa_entry_id
            task.cleaned_title = title
            task.cleaned_content = cleaned_content
            task.status = AnswerKnowledgeStatus.COMPLETE
            task.error = None
            task.finished_at = utc_now()
            db.commit()

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

    @staticmethod
    def _fail(task_id: int, exc: Exception) -> None:
        with SessionLocal() as db:
            task = db.get(AnswerKnowledgeTask, task_id)
            if task is None:
                return
            task.status = AnswerKnowledgeStatus.FAILED
            task.error = f"{type(exc).__name__}: {exc}"[:4000]
            task.finished_at = utc_now()
            db.commit()


answer_knowledge_service = AnswerKnowledgeService()
