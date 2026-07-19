from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import AnswerOrigin, MessageRole, MessageStatus
from app.models.orm import Conversation, Message, User, is_guest_user
from app.rag.generation import generator, validate_citations
from app.rag.retrieval import RetrievalResult, retrieval_service
from app.services.chat_scope import (
    NO_EVIDENCE_REFUSALS,
    OUT_OF_SCOPE_REFUSALS,
    is_hohai_related,
    refusal_for,
    scope_hohai_query,
    social_response,
)
from app.services.qa_knowledge import QaLookup, QaResolvedSource, qa_knowledge_service
from app.services.web_search import WebSearchError, WebSearchResult, get_web_search_provider

__all__ = ("NO_EVIDENCE_REFUSALS", "OUT_OF_SCOPE_REFUSALS", "ChatService", "chat_service")

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
    @staticmethod
    def is_hohai_related(question: str) -> bool:
        return is_hohai_related(question)

    @staticmethod
    def refusal_for(question: str, *, out_of_scope: bool) -> str:
        return refusal_for(question, out_of_scope=out_of_scope)

    @staticmethod
    def social_response(question: str) -> str | None:
        return social_response(question)

    def prepare(
        self, db: Session, user: User, question: str, conversation_id: int | None
    ) -> tuple[Conversation, Message, list[dict[str, str]]]:
        if is_guest_user(user):
            # 访客单轮无痕：不建会话、不写消息、无历史；conversation_id 一律忽略（防带他人会话号探询）。
            # transient 对象（永不 db.add），刻意省略 user_id/conversation_id 让外键自然为 None。
            conversation = Conversation(title=question[:40])
            assistant = Message(
                role=MessageRole.ASSISTANT,
                content="",
                status=MessageStatus.STREAMING,
                model=settings.llm_model,
            )
            return conversation, assistant, []

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
        self,
        question: str,
        history: list[dict[str, str]],
        query_vector=None,  # type: ignore[no-untyped-def]
    ) -> tuple[str, list[RetrievalResult]]:
        standalone = self._retrieval_query(question, history)
        return standalone, retrieval_service.search(standalone, query_vector=query_vector)

    def search_web(self, query: str) -> list[WebSearchResult]:
        if not settings.web_search_enabled:
            return []
        return get_web_search_provider().search(query)

    @staticmethod
    def _retrieval_query(question: str, history: list[dict[str, str]]) -> str:
        """Resolve only genuinely context-dependent follow-ups without an LLM call."""
        resolved = question
        if history:
            normalized = question.strip().rstrip("，。？！!")
            needs_context = any(marker in normalized for marker in CONTEXT_REFERENCE_MARKERS)
            needs_context = needs_context or normalized in SHORT_CONTEXT_QUESTIONS
            if needs_context:
                previous_user = next(
                    (item["content"] for item in reversed(history) if item.get("role") == "user"),
                    "",
                )
                if previous_user:
                    resolved = f"{previous_user} {question}".strip()
        return scope_hohai_query(resolved)

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
    def evidence_is_sufficient(question: str, results: list[RetrievalResult]) -> bool:
        if not results:
            return False
        if not settings.evidence_sufficiency_check_enabled:
            return True
        try:
            return generator.evidence_is_sufficient(question, results)
        except Exception as exc:
            logger.warning("Evidence sufficiency check failed; using web fallback: %s", exc)
            return False

    @staticmethod
    def _compact_citations(
        answer: str, cited: list[int], marker: str
    ) -> tuple[str, dict[int, int]]:
        """Renumber the sources that survived citation filtering without gaps."""
        mapping = {old_index: new_index for new_index, old_index in enumerate(cited, start=1)}
        if not mapping:
            return answer, mapping

        def replace(match: re.Match[str]) -> str:
            old_index = int(match.group(1))
            new_index = mapping.get(old_index)
            return f"[{marker}{new_index}]" if new_index is not None else ""

        return re.sub(rf"\[{marker}(\d+)\]", replace, answer), mapping

    @staticmethod
    def _answer_origin_for_sources(
        sources: list[dict[str, object]],
    ) -> AnswerOrigin:
        has_web = any(source.get("source_type") == "WEB_SEARCH" for source in sources)
        has_local = any(source.get("source_type") != "WEB_SEARCH" for source in sources)
        if has_local and has_web:
            return AnswerOrigin.HYBRID
        if has_web:
            return AnswerOrigin.WEB_SEARCH
        if has_local:
            return AnswerOrigin.KNOWLEDGE_BASE
        return AnswerOrigin.NO_ANSWER

    @staticmethod
    def grounded_answer(
        raw_answer: str, results: list[RetrievalResult]
    ) -> tuple[str, list[dict[str, object]], list[int]]:
        """Validate citations and expose only the strongly related context sources."""
        answer, cited = validate_citations(raw_answer, len(results), "S")
        if results and not cited:
            answer = f"{answer} [S1]".strip()
            cited = [1]
        answer, citation_mapping = ChatService._compact_citations(answer, cited, "S")
        sources = [
            results[index - 1].source_dict(citation_index=citation_mapping[index])
            for index in cited
        ]
        for source, result in zip(sources, (results[index - 1] for index in cited), strict=False):
            source["source_type"] = result.document_kind
        return answer, sources, list(range(1, len(cited) + 1))

    @staticmethod
    def grounded_web_answer(
        raw_answer: str, results: list[WebSearchResult]
    ) -> tuple[str, list[dict[str, object]], list[int]]:
        answer, cited = validate_citations(raw_answer, len(results), "W")
        if results and not cited:
            answer = f"{answer} [W1]".strip()
            cited = [1]
        answer, citation_mapping = ChatService._compact_citations(answer, cited, "W")
        sources = []
        for index in cited:
            source = results[index - 1].source_dict()
            source["citation_index"] = citation_mapping[index]
            sources.append(source)
        return answer, sources, list(range(1, len(cited) + 1))

    @staticmethod
    def grounded_mixed_answer(
        raw_answer: str,
        local_results: list[RetrievalResult],
        web_results: list[WebSearchResult],
    ) -> tuple[str, list[dict[str, object]]]:
        answer, cited_local = validate_citations(raw_answer, len(local_results), "S")
        answer, cited_web = validate_citations(answer, len(web_results), "W")
        if not cited_local and not cited_web:
            if web_results:
                answer = f"{answer} [W1]".strip()
                cited_web = [1]
            elif local_results:
                answer = f"{answer} [S1]".strip()
                cited_local = [1]
        answer, local_mapping = ChatService._compact_citations(answer, cited_local, "S")
        answer, web_mapping = ChatService._compact_citations(answer, cited_web, "W")
        sources: list[dict[str, object]] = []
        for index in cited_local:
            result = local_results[index - 1]
            source = result.source_dict(citation_index=local_mapping[index])
            source["source_type"] = result.document_kind
            sources.append(source)
        for index in cited_web:
            source = web_results[index - 1].source_dict()
            source["citation_index"] = web_mapping[index]
            sources.append(source)
        return answer, sources[: settings.context_top_k]

    @staticmethod
    def grounded_qa_answer(
        raw_answer: str, sources: tuple[QaResolvedSource, ...]
    ) -> tuple[str, list[dict[str, object]]]:
        available = {(source.marker, source.citation_index): source for source in sources}
        cited: list[tuple[str, int]] = []

        def replace(match: re.Match[str]) -> str:
            key = (match.group(1), int(match.group(2)))
            if key not in available:
                return ""
            if key not in cited:
                cited.append(key)
            return match.group(0)

        answer = re.sub(r"\[([SW])(\d+)\]", replace, raw_answer).strip()
        if not cited and sources:
            first = sources[0]
            cited.append((first.marker, first.citation_index))
            answer = f"{answer} [{first.marker}{first.citation_index}]".strip()
        citation_mappings: dict[str, dict[int, int]] = {}
        for marker in {marker for marker, _index in cited}:
            marker_indexes = [index for item_marker, index in cited if item_marker == marker]
            answer, citation_mappings[marker] = ChatService._compact_citations(
                answer, marker_indexes, marker
            )
        grounded_sources: list[dict[str, object]] = []
        for marker, index in cited[: settings.context_top_k]:
            source = available[(marker, index)].source_dict()
            source["citation_index"] = citation_mappings[marker][index]
            grounded_sources.append(source)
        return answer, grounded_sources

    def complete(
        self,
        db: Session,
        user: User,
        question: str,
        conversation_id: int | None,
    ) -> dict[str, object]:
        started = time.perf_counter()
        guest = is_guest_user(user)
        conversation, assistant, history = self.prepare(db, user, question, conversation_id)
        try:
            standalone = self._retrieval_query(question, history)
            qa_lookup = qa_knowledge_service.lookup(standalone)
            retrieved: list[RetrievalResult] = []
            answer_origin = AnswerOrigin.NO_ANSWER
            actual_model = settings.llm_model
            retrieval_score: float | None = None

            qa_results = [source.result for source in qa_lookup.sources]
            qa_is_usable = (
                qa_lookup.mode in {"direct", "assist"}
                and qa_lookup.match is not None
                and self.evidence_is_sufficient(question, qa_results)
            )
            if qa_lookup.match is not None:
                retrieval_score = qa_lookup.match.score

            if qa_is_usable and qa_lookup.match is not None:
                raw_answer = generator.complete_qa(
                    question, qa_lookup.match.answer, list(qa_lookup.sources)
                )
                if not raw_answer.strip():
                    raise RuntimeError("LLM returned an empty QA-grounded answer")
                answer, sources = self.grounded_qa_answer(raw_answer, qa_lookup.sources)
                answer_origin = AnswerOrigin.KNOWLEDGE_BASE
            else:
                if qa_lookup.query_vector is None:
                    _standalone, retrieved = self.retrieve(question, history)
                else:
                    _standalone, retrieved = self.retrieve(
                        question, history, query_vector=qa_lookup.query_vector
                    )
                results = self.valid_local_context(retrieved)
                if retrieved:
                    retrieval_score = retrieved[0].score
                if results and self.evidence_is_sufficient(question, results):
                    raw_answer = generator.complete(question, results)
                    if not raw_answer.strip():
                        raise RuntimeError("LLM returned an empty answer")
                    answer, sources, _cited = self.grounded_answer(raw_answer, results)
                    answer_origin = AnswerOrigin.KNOWLEDGE_BASE
                else:
                    answer, sources = self._complete_with_web(
                        question, standalone, assistant.id, results
                    )
                    answer_origin = self._answer_origin_for_sources(sources)

            if answer_origin == AnswerOrigin.NO_ANSWER:
                sources = []
            latency = int((time.perf_counter() - started) * 1000)
            assistant.content = answer
            assistant.sources_json = sources
            assistant.status = MessageStatus.COMPLETE
            assistant.latency_ms = latency
            assistant.retrieval_score = retrieval_score
            assistant.answer_origin = answer_origin
            assistant.model = actual_model
            if not guest:  # 访客无痕：transient 对象零脏写，跳过 commit 表达意图并防未来漂移
                db.commit()
            return {
                "conversation_id": conversation.id,
                "message_id": assistant.id,
                "answer": answer,
                "sources": sources,
                "answer_origin": answer_origin.value,
                "model": actual_model,
                "latency_ms": latency,
            }
        except Exception:
            assistant.status = MessageStatus.ERROR
            if not guest:
                db.commit()
            raise

    def _complete_with_web(
        self,
        question: str,
        standalone: str,
        assistant_id: int,
        local_results: list[RetrievalResult],
    ) -> tuple[str, list[dict[str, object]]]:
        fallback = self._web_scope_fallback(standalone, assistant_id)
        if fallback is not None:
            return fallback, []
        web_results = self._safe_web_search(standalone, assistant_id)
        if not web_results:
            return self.refusal_for(standalone, out_of_scope=False), []
        if local_results:
            local_limit = min(2, len(local_results))
            web_limit = max(1, settings.context_top_k - local_limit)
            local_context = local_results[:local_limit]
            web_context = web_results[:web_limit]
            for index, result in enumerate(web_context, start=1):
                result.citation_index = index
            raw_answer = generator.complete_mixed(question, local_context, web_context)
            if not raw_answer.strip():
                raise RuntimeError("LLM returned an empty mixed answer")
            return self.grounded_mixed_answer(raw_answer, local_context, web_context)
        web_context = web_results[: settings.context_top_k]
        for index, result in enumerate(web_context, start=1):
            result.citation_index = index
        raw_answer = generator.complete_web(question, web_context)
        if not raw_answer.strip():
            raise RuntimeError("LLM returned an empty web answer")
        answer, sources, _cited = self.grounded_web_answer(raw_answer, web_context)
        return answer, sources

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
        sources: list[dict[str, object]] = []
        local_results: list[RetrievalResult] = []
        web_results: list[WebSearchResult] = []
        qa_lookup: QaLookup | None = None
        answer_origin = AnswerOrigin.NO_ANSWER
        actual_model = settings.llm_model
        retrieval_score: float | None = None
        mode = "refusal"
        fallback_answer: str | None = None
        try:
            standalone = self._retrieval_query(question, history)
            yield sse("status", {"phase": "qa_retrieval", "message": "正在优先匹配问答知识..."})
            qa_lookup = qa_knowledge_service.lookup(standalone)

            qa_results = [source.result for source in qa_lookup.sources]
            qa_is_usable = (
                qa_lookup.mode in {"direct", "assist"}
                and qa_lookup.match is not None
                and self.evidence_is_sufficient(question, qa_results)
            )
            if qa_lookup.match is not None:
                retrieval_score = qa_lookup.match.score
                yield sse(
                    "status",
                    {"phase": "qa_sources", "message": "已命中相似问答，正在核验关联资料..."},
                )

            if qa_is_usable and qa_lookup.match is not None:
                mode = "qa"
                answer_origin = AnswerOrigin.KNOWLEDGE_BASE
                for delta in generator.stream_qa(
                    question, qa_lookup.match.answer, list(qa_lookup.sources)
                ):
                    full_answer += delta
                    yield sse("delta", {"text": delta})
            else:
                retrieval_message = (
                    "相似问答的关联资料不足，正在检索完整知识库..."
                    if qa_lookup.match is not None
                    else "正在检索校园知识库..."
                )
                yield sse("status", {"phase": "retrieval", "message": retrieval_message})
                if qa_lookup.query_vector is None:
                    _standalone, retrieved = self.retrieve(question, history)
                else:
                    _standalone, retrieved = self.retrieve(
                        question, history, query_vector=qa_lookup.query_vector
                    )
                if retrieved:
                    retrieval_score = retrieved[0].score
                local_results = self.valid_local_context(retrieved)
                if local_results and self.evidence_is_sufficient(question, local_results):
                    mode = "local"
                    answer_origin = AnswerOrigin.KNOWLEDGE_BASE
                    yield sse(
                        "status", {"phase": "generation", "message": "正在组织有依据的回答..."}
                    )
                    for delta in generator.stream(question, local_results):
                        full_answer += delta
                        yield sse("delta", {"text": delta})
                else:
                    mode = "mixed" if local_results else "web"

            if mode in {"web", "mixed"}:
                fallback_answer = self._web_scope_fallback(standalone, assistant_id)
                if fallback_answer is not None:
                    mode = "refusal"
                else:
                    yield sse(
                        "status", {"phase": "web_search", "message": "正在联网补充缺失信息..."}
                    )
                    web_results = self._safe_web_search(standalone, assistant_id)
                if mode != "refusal" and web_results:
                    yield sse(
                        "status", {"phase": "generation", "message": "正在整理联网搜索结果..."}
                    )
                    deltas, local_results, web_results, answer_origin = self._prepare_web_stream(
                        question, mode, local_results, web_results
                    )
                    for delta in deltas:
                        full_answer += delta
                        yield sse("delta", {"text": delta})
                elif mode != "refusal":
                    fallback_answer = self.refusal_for(standalone, out_of_scope=False)
                    mode = "refusal"

            if mode == "refusal":
                full_answer = fallback_answer or self.refusal_for(
                    standalone, out_of_scope=not self.is_hohai_related(standalone)
                )
                answer_origin = AnswerOrigin.NO_ANSWER
                yield sse("delta", {"text": full_answer})

            if not full_answer.strip():
                raise RuntimeError("LLM stream returned no answer content")
            original_answer = full_answer.strip()
            cleaned, sources = self._ground_stream_answer(
                mode,
                full_answer,
                qa_lookup,
                local_results,
                web_results,
            )
            answer_origin = self._answer_origin_for_sources(sources)
            if cleaned.startswith(original_answer) and cleaned != original_answer:
                yield sse("delta", {"text": cleaned[len(original_answer) :]})
            yield sse(
                "sources",
                {
                    "items": sources,
                    "answer": cleaned,
                    "low_confidence": answer_origin == AnswerOrigin.NO_ANSWER,
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
                retrieval_score=retrieval_score,
                answer_origin=answer_origin,
                model=actual_model,
            )
            yield sse(
                "done",
                {
                    "latency_ms": latency,
                    "model": actual_model,
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
                model=actual_model,
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
                model=actual_model,
            )
            yield sse("error", {"code": "CHAT_FAILED", "message": "回答生成失败，请稍后重试"})

    @staticmethod
    def _prepare_web_stream(
        question: str,
        mode: str,
        local_results: list[RetrievalResult],
        web_results: list[WebSearchResult],
    ) -> tuple[
        Iterator[str],
        list[RetrievalResult],
        list[WebSearchResult],
        AnswerOrigin,
    ]:
        if mode == "mixed":
            local_context = local_results[:2]
            web_limit = max(1, settings.context_top_k - len(local_context))
            web_context = web_results[:web_limit]
            for index, result in enumerate(web_context, start=1):
                result.citation_index = index
            return (
                generator.stream_mixed(question, local_context, web_context),
                local_context,
                web_context,
                AnswerOrigin.HYBRID,
            )
        web_context = web_results[: settings.context_top_k]
        for index, result in enumerate(web_context, start=1):
            result.citation_index = index
        return (
            generator.stream_web(question, web_context),
            local_results,
            web_context,
            AnswerOrigin.WEB_SEARCH,
        )

    def _ground_stream_answer(
        self,
        mode: str,
        answer: str,
        qa_lookup: QaLookup | None,
        local_results: list[RetrievalResult],
        web_results: list[WebSearchResult],
    ) -> tuple[str, list[dict[str, object]]]:
        if mode == "qa" and qa_lookup is not None:
            return self.grounded_qa_answer(answer, qa_lookup.sources)
        if mode == "local":
            cleaned, sources, _cited = self.grounded_answer(answer, local_results)
            return cleaned, sources
        if mode == "mixed":
            return self.grounded_mixed_answer(answer, local_results, web_results)
        if mode == "web":
            cleaned, sources, _cited = self.grounded_web_answer(answer, web_results)
            return cleaned, sources
        return answer.strip(), []

    def _web_scope_fallback(self, query: str, assistant_id: int) -> str | None:
        social = self.social_response(query)
        if social is not None:
            return social
        if self.is_hohai_related(query):
            return None
        logger.info(
            "Skipped web search for an out-of-scope question assistant_id=%s",
            assistant_id,
        )
        return self.refusal_for(query, out_of_scope=True)

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
        model: str | None = None,
    ) -> None:
        if assistant_id is None:
            return  # 访客消息未落库（transient，id 恒 None），无可回写
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
            if model is not None:
                message.model = model
            conversation = db.get(Conversation, message.conversation_id)
            if conversation is not None:
                conversation.updated_at = utc_now()
            db.commit()


chat_service = ChatService()
