from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import MessageRole, MessageStatus
from app.models.orm import Conversation, Message, User
from app.rag.generation import generator, validate_citations
from app.rag.retrieval import RetrievalResult, retrieval_service

REFUSAL = "根据现有校园知识库，暂未找到足够相关的信息。建议补充问题细节或通过河海大学官网核实。"
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ChatService:
    def prepare(
        self, db: Session, user: User, question: str, conversation_id: int | None
    ) -> tuple[Conversation, Message, list[dict[str, str]]]:
        if conversation_id is not None:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user.id,
                )
            )
            if conversation is None:
                raise LookupError("会话不存在")
        else:
            conversation = Conversation(user_id=user.id, title=question[:40])
            db.add(conversation)
            db.flush()

        previous = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .limit(6)
        ).all()
        history = [
            {"role": message.role.value.lower(), "content": message.content}
            for message in reversed(previous)
            if message.status == MessageStatus.COMPLETE
        ]
        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=question,
                status=MessageStatus.COMPLETE,
            )
        )
        assistant = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="",
            status=MessageStatus.STREAMING,
            model=settings.llm_model,
        )
        db.add(assistant)
        conversation.updated_at = utc_now()
        db.commit()
        db.refresh(conversation)
        db.refresh(assistant)
        return conversation, assistant, history

    def retrieve(
        self, question: str, history: list[dict[str, str]]
    ) -> tuple[str, list[RetrievalResult]]:
        standalone = generator.rewrite_query(question, history) if history else question
        return standalone, retrieval_service.search(standalone)

    @staticmethod
    def is_low_confidence(results: list[RetrievalResult]) -> bool:
        return not results or results[0].score < settings.retrieval_min_score

    def complete(
        self,
        db: Session,
        user: User,
        question: str,
        conversation_id: int | None,
    ) -> dict[str, object]:
        started = time.perf_counter()
        conversation, assistant, history = self.prepare(db, user, question, conversation_id)
        try:
            _standalone, results = self.retrieve(question, history)
            if self.is_low_confidence(results):
                answer = REFUSAL
                sources: list[dict[str, object]] = []
            else:
                raw_answer = generator.complete(question, results)
                answer, cited = validate_citations(raw_answer, len(results))
                selected = [results[index - 1] for index in cited] if cited else results
                sources = [result.source_dict() for result in selected]
            latency = int((time.perf_counter() - started) * 1000)
            assistant.content = answer
            assistant.sources_json = sources
            assistant.status = MessageStatus.COMPLETE
            assistant.latency_ms = latency
            assistant.retrieval_score = results[0].score if results else None
            db.commit()
            return {
                "conversation_id": conversation.id,
                "message_id": assistant.id,
                "answer": answer,
                "sources": sources,
                "model": settings.llm_model,
                "latency_ms": latency,
            }
        except Exception:
            assistant.status = MessageStatus.ERROR
            db.commit()
            raise

    def stream(
        self,
        conversation_id: int,
        assistant_id: int,
        question: str,
        history: list[dict[str, str]],
    ) -> Iterator[str]:
        started = time.perf_counter()
        yield sse("start", {"conversation_id": conversation_id, "message_id": assistant_id})
        full_answer = ""
        results: list[RetrievalResult] = []
        sources: list[dict[str, object]] = []
        try:
            _standalone, results = self.retrieve(question, history)
            if self.is_low_confidence(results):
                full_answer = REFUSAL
                yield sse("sources", {"items": [], "low_confidence": True})
                yield sse("delta", {"text": full_answer})
            else:
                sources = [result.source_dict() for result in results]
                yield sse("sources", {"items": sources, "low_confidence": False})
                for delta in generator.stream(question, results):
                    full_answer += delta
                    yield sse("delta", {"text": delta})
            cleaned, cited = validate_citations(full_answer, len(results))
            if cited:
                sources = [results[index - 1].source_dict() for index in cited]
            latency = int((time.perf_counter() - started) * 1000)
            self._finalize(
                assistant_id,
                content=cleaned,
                sources=sources,
                status=MessageStatus.COMPLETE,
                latency_ms=latency,
                retrieval_score=results[0].score if results else None,
            )
            yield sse("done", {"latency_ms": latency, "model": settings.llm_model})
        except GeneratorExit:
            self._finalize(
                assistant_id,
                content=full_answer,
                sources=sources,
                status=MessageStatus.CANCELLED,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            raise
        except Exception:
            logger.exception("流式回答失败: assistant_id=%s", assistant_id)
            self._finalize(
                assistant_id,
                content=full_answer,
                sources=sources,
                status=MessageStatus.ERROR,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            yield sse(
                "error",
                {"code": "CHAT_FAILED", "message": "回答生成失败，请稍后重试"},
            )

    @staticmethod
    def _finalize(
        assistant_id: int,
        *,
        content: str,
        sources: list[dict[str, object]],
        status: MessageStatus,
        latency_ms: int,
        retrieval_score: float | None = None,
    ) -> None:
        with SessionLocal() as db:
            message = db.get(Message, assistant_id)
            if message is None:
                return
            message.content = content
            message.sources_json = sources
            message.status = status
            message.latency_ms = latency_ms
            message.retrieval_score = retrieval_score
            conversation = db.get(Conversation, message.conversation_id)
            if conversation is not None:
                conversation.updated_at = utc_now()
            db.commit()


chat_service = ChatService()
