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
from app.models.enums import AnswerOrigin, MessageRole, MessageStatus
from app.models.orm import Conversation, Message, User
from app.rag.generation import generator, validate_citations
from app.rag.retrieval import RetrievalResult, retrieval_service
from app.services.web_search import WebSearchError, WebSearchResult, get_web_search_provider

REFUSAL = (
    "根据现有校园知识库和联网搜索结果，暂未找到足够相关的信息。"
    "建议补充问题细节，或通过河海大学官网核实。"
)
logger = logging.getLogger("uvicorn.error")

CONTEXT_REFERENCE_MARKERS = (
    "它",
    "这个",
    "那个",
    "上述",
    "上面",
    "该项",
    "该校",
    "其中",
    "前者",
    "后者",
    "刚才",
    "这些",
    "那些",
)
SHORT_CONTEXT_QUESTIONS = {
    "什么时候",
    "在哪里",
    "怎么办",
    "怎么做",
    "有哪些",
    "多少",
    "为什么",
    "然后呢",
    "还有呢",
}


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
        standalone = self._retrieval_query(question, history)
        return standalone, retrieval_service.search(standalone)

    def search_web(self, query: str) -> list[WebSearchResult]:
        if not settings.web_search_enabled:
            return []
        return get_web_search_provider().search(query)

    @staticmethod
    def _retrieval_query(question: str, history: list[dict[str, str]]) -> str:
        """Resolve only genuinely context-dependent follow-ups without an LLM call."""
        if not history:
            return question
        normalized = question.strip().rstrip("，。？！!")
        needs_context = any(marker in normalized for marker in CONTEXT_REFERENCE_MARKERS)
        needs_context = needs_context or normalized in SHORT_CONTEXT_QUESTIONS
        if not needs_context:
            return question
        previous_user = next(
            (item["content"] for item in reversed(history) if item.get("role") == "user"),
            "",
        )
        return f"{previous_user} {question}".strip() if previous_user else question

    @staticmethod
    def is_low_confidence(results: list[RetrievalResult]) -> bool:
        if not results:
            return True
        top = results[0]
        if top.score >= settings.retrieval_min_score:
            return False
        strong_lexical_match = (
            top.score >= settings.retrieval_lexical_override_score
            and top.lexical_coverage >= settings.retrieval_lexical_min_coverage
            and top.dense_rank is not None
            and top.dense_rank <= settings.retrieval_hybrid_max_rank
            and top.sparse_rank is not None
            and top.sparse_rank <= settings.retrieval_hybrid_max_rank
        )
        if strong_lexical_match:
            logger.info(
                "Retrieval threshold overridden by hybrid lexical evidence "
                "document=%s score=%.4f coverage=%.2f dense_rank=%s sparse_rank=%s",
                top.document_id,
                top.score,
                top.lexical_coverage,
                top.dense_rank,
                top.sparse_rank,
            )
        return not strong_lexical_match

    @staticmethod
    def relevant_context(results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Keep only strongly related chunks, while retaining at most the configured Top-K."""
        if not results:
            return []
        top_score = results[0].score
        cutoff = max(
            settings.retrieval_context_min_score,
            top_score - settings.retrieval_context_score_margin,
        )
        selected = [results[0]]
        selected.extend(result for result in results[1:] if result.score >= cutoff)
        return selected[: settings.context_top_k]

    def valid_local_context(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        if self.is_low_confidence(results):
            return []
        return self.relevant_context(results)

    @staticmethod
    def grounded_answer(
        raw_answer: str, results: list[RetrievalResult]
    ) -> tuple[str, list[dict[str, object]], list[int]]:
        """Validate citations and expose only the strongly related context sources."""
        answer, cited = validate_citations(raw_answer, len(results), "S")
        if results and not cited:
            answer = f"{answer} [S1]".strip()
            cited = [1]
        sources = [
            result.source_dict(citation_index=index)
            for index, result in enumerate(results, start=1)
        ]
        for source in sources:
            source["source_type"] = "KNOWLEDGE_BASE"
        return answer, sources, cited

    @staticmethod
    def grounded_web_answer(
        raw_answer: str, results: list[WebSearchResult]
    ) -> tuple[str, list[dict[str, object]], list[int]]:
        answer, cited = validate_citations(raw_answer, len(results), "W")
        if results and not cited:
            answer = f"{answer} [W1]".strip()
            cited = [1]
        sources = [result.source_dict() for result in results]
        return answer, sources, cited

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
            standalone, retrieved = self.retrieve(question, history)
            results = self.valid_local_context(retrieved)
            answer_origin = AnswerOrigin.NO_ANSWER
            if results:
                raw_answer = generator.complete(question, results)
                if not raw_answer.strip():
                    raise RuntimeError("LLM returned an empty answer")
                answer, sources, _cited = self.grounded_answer(raw_answer, results)
                answer_origin = AnswerOrigin.KNOWLEDGE_BASE
            else:
                web_results = self._safe_web_search(standalone, assistant.id)
                if web_results:
                    raw_answer = generator.complete_web(question, web_results)
                    if not raw_answer.strip():
                        raise RuntimeError("LLM returned an empty web answer")
                    answer, sources, _cited = self.grounded_web_answer(raw_answer, web_results)
                    answer_origin = AnswerOrigin.WEB_SEARCH
                else:
                    answer = REFUSAL
                    sources = []
            latency = int((time.perf_counter() - started) * 1000)
            assistant.content = answer
            assistant.sources_json = sources
            assistant.status = MessageStatus.COMPLETE
            assistant.latency_ms = latency
            assistant.retrieval_score = retrieved[0].score if retrieved else None
            assistant.answer_origin = answer_origin
            db.commit()
            return {
                "conversation_id": conversation.id,
                "message_id": assistant.id,
                "answer": answer,
                "sources": sources,
                "answer_origin": answer_origin.value,
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
        local_results: list[RetrievalResult] = []
        web_results: list[WebSearchResult] = []
        sources: list[dict[str, object]] = []
        answer_origin = AnswerOrigin.NO_ANSWER
        retrieved: list[RetrievalResult] = []
        try:
            yield sse("status", {"phase": "retrieval", "message": "正在检索校园知识库..."})
            retrieval_started = time.perf_counter()
            standalone, retrieved = self.retrieve(question, history)
            logger.info(
                "Chat retrieval completed assistant_id=%s elapsed=%.2fs results=%d",
                assistant_id,
                time.perf_counter() - retrieval_started,
                len(retrieved),
            )
            local_results = self.valid_local_context(retrieved)
            if local_results:
                logger.info(
                    "Chat context filtered assistant_id=%s retrieved=%d selected=%d "
                    "cutoff_floor=%.2f",
                    assistant_id,
                    len(retrieved),
                    len(local_results),
                    settings.retrieval_context_min_score,
                )
                yield sse("status", {"phase": "generation", "message": "正在组织有依据的回答..."})
                generation_started = time.perf_counter()
                first_delta_at: float | None = None
                for delta in generator.stream(question, local_results):
                    if first_delta_at is None:
                        first_delta_at = time.perf_counter()
                        logger.info(
                            "Chat first LLM token assistant_id=%s elapsed=%.2fs",
                            assistant_id,
                            first_delta_at - generation_started,
                        )
                    full_answer += delta
                    yield sse("delta", {"text": delta})
                answer_origin = AnswerOrigin.KNOWLEDGE_BASE
            else:
                yield sse("status", {"phase": "web_search", "message": "正在联网搜索最新信息..."})
                web_results = self._safe_web_search(standalone, assistant_id)
                if web_results:
                    yield sse(
                        "status",
                        {"phase": "generation", "message": "正在整理联网搜索结果..."},
                    )
                    generation_started = time.perf_counter()
                    first_delta_at = None
                    for delta in generator.stream_web(question, web_results):
                        if first_delta_at is None:
                            first_delta_at = time.perf_counter()
                            logger.info(
                                "Chat first web LLM token assistant_id=%s elapsed=%.2fs",
                                assistant_id,
                                first_delta_at - generation_started,
                            )
                        full_answer += delta
                        yield sse("delta", {"text": delta})
                    answer_origin = AnswerOrigin.WEB_SEARCH
                else:
                    full_answer = REFUSAL
                    yield sse("delta", {"text": full_answer})

            if not full_answer.strip():
                raise RuntimeError("LLM stream returned no answer content")
            logger.info(
                "Chat LLM stream completed assistant_id=%s chars=%d origin=%s",
                assistant_id,
                len(full_answer),
                answer_origin.value,
            )
            original_answer = full_answer.strip()
            if answer_origin == AnswerOrigin.WEB_SEARCH:
                cleaned, sources, _cited = self.grounded_web_answer(full_answer, web_results)
            elif answer_origin == AnswerOrigin.KNOWLEDGE_BASE:
                cleaned, sources, _cited = self.grounded_answer(full_answer, local_results)
            else:
                cleaned, sources = original_answer, []
            if cleaned.startswith(original_answer) and cleaned != original_answer:
                yield sse("delta", {"text": cleaned[len(original_answer) :]})
            yield sse(
                "sources",
                {
                    "items": sources,
                    "low_confidence": not local_results,
                    "answer_origin": answer_origin.value,
                    "final": True,
                },
            )
            latency = int((time.perf_counter() - started) * 1000)
            self._finalize(
                assistant_id,
                content=cleaned,
                sources=sources,
                status=MessageStatus.COMPLETE,
                latency_ms=latency,
                retrieval_score=retrieved[0].score if retrieved else None,
                answer_origin=answer_origin,
            )
            yield sse(
                "done",
                {
                    "latency_ms": latency,
                    "model": settings.llm_model,
                    "answer_origin": answer_origin.value,
                },
            )
        except GeneratorExit:
            self._finalize(
                assistant_id,
                content=full_answer,
                sources=sources,
                status=MessageStatus.CANCELLED,
                latency_ms=int((time.perf_counter() - started) * 1000),
                answer_origin=answer_origin,
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
                answer_origin=answer_origin,
            )
            yield sse(
                "error",
                {"code": "CHAT_FAILED", "message": "回答生成失败，请稍后重试"},
            )

    def _safe_web_search(self, query: str, assistant_id: int) -> list[WebSearchResult]:
        try:
            results = self.search_web(query)
        except WebSearchError as exc:
            logger.warning(
                "Web search failed assistant_id=%s kind=%s detail=%s",
                assistant_id,
                exc.kind,
                exc,
            )
            return []
        if not results:
            logger.info("Web search returned no results assistant_id=%s", assistant_id)
        return results

    @staticmethod
    def _finalize(
        assistant_id: int,
        *,
        content: str,
        sources: list[dict[str, object]],
        status: MessageStatus,
        latency_ms: int,
        retrieval_score: float | None = None,
        answer_origin: AnswerOrigin | None = None,
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
            message.answer_origin = answer_origin
            conversation = db.get(Conversation, message.conversation_id)
            if conversation is not None:
                conversation.updated_at = utc_now()
            db.commit()


chat_service = ChatService()
