from __future__ import annotations

import numpy as np
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import AnswerKnowledgeStatus, AnswerOrigin, MessageRole, MessageStatus, Role
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
from app.rag.index import index_manager
from app.services.answer_knowledge import answer_knowledge_service
from app.services.documents import document_service
from app.services.qa_knowledge import qa_knowledge_service, rewrite_qa_queries
from sqlalchemy import func, select


def fake_vectors(texts: list[str]) -> np.ndarray:
    vectors = np.zeros((len(texts), 8), dtype=np.float32)
    vectors[:, 0] = 1.0
    return vectors


def test_qa_query_rewrite_scopes_campus_and_expands_common_synonyms() -> None:
    assert rewrite_qa_queries("有几个学院？") == (
        "河海大学有几个学院",
        "河海大学有多少个学院",
    )
    assert rewrite_qa_queries("河海大学有多少个学院？") == (
        "河海大学有多少个学院",
        "河海大学有几个学院",
    )
    assert rewrite_qa_queries("1+1等于几？") == ("1+1等于几",)


def create_user() -> int:
    with SessionLocal() as db:
        user = User(
            name="满意回答用户",
            email="answer-kb@example.com",
            password_hash=hash_password("safe-pass-123"),
            role=Role.STUDENT,
        )
        db.add(user)
        db.commit()
        return user.id


def create_source_document(user_id: int) -> tuple[int, int]:
    with SessionLocal() as db:
        document, job = document_service.save_upload(
            db,
            data="# 新生报到指南\n\n新生报到需要携带录取通知书和有效身份证件。".encode(),
            original_name="guide.md",
            mime_type="text/markdown",
            title="新生报到指南",
            category="报到",
            uploaded_by=user_id,
            enqueue=False,
        )
        document_id = document.id
        job_id = job.id
    document_service.process(document_id, job_id, rebuild=True)
    return document_id, index_manager.stable_chunk_id(document_id, 0)


def create_answer_message(
    user_id: int,
    *,
    question: str,
    answer: str,
    sources: list[dict[str, object]],
    origin: AnswerOrigin,
) -> int:
    with SessionLocal() as db:
        conversation = Conversation(user_id=user_id, title=question[:40])
        db.add(conversation)
        db.flush()
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
            content=answer,
            sources_json=sources,
            status=MessageStatus.COMPLETE,
            answer_origin=origin,
        )
        db.add(assistant)
        db.commit()
        return assistant.id


def run_task(user_id: int, assistant_id: int) -> AnswerKnowledgeTask:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        task_id = answer_knowledge_service.create_task(db, user, assistant_id).id
    answer_knowledge_service.process(task_id)
    with SessionLocal() as db:
        task = db.get(AnswerKnowledgeTask, task_id)
        assert task is not None
        db.expunge(task)
        return task


def test_hidden_qa_reuses_original_document_and_deduplicates(monkeypatch) -> None:
    monkeypatch.setattr(answer_knowledge_service, "submit", lambda _task_id: None)
    monkeypatch.setattr(embedding.embedder, "embed_documents", fake_vectors)
    monkeypatch.setattr(embedding.embedder, "embed_query", lambda _text: fake_vectors([""])[0])
    monkeypatch.setattr(
        "app.services.answer_knowledge.generator.clean_answer_for_knowledge",
        lambda **_kwargs: (
            "# 新生报到材料\n\n"
            "## 标准问题\n新生报到需要准备哪些材料？\n\n"
            "## 标准答案\n新生报到应携带录取通知书和有效身份证件。[S1]"
        ),
    )
    user_id = create_user()
    document_id, chunk_id = create_source_document(user_id)
    source = {
        "source_type": "KNOWLEDGE_BASE",
        "citation_index": 1,
        "document_id": document_id,
        "chunk_id": chunk_id,
        "title": "新生报到指南",
        "snippet": "新生报到需要携带录取通知书和有效身份证件。",
    }
    first_message = create_answer_message(
        user_id,
        question="新生报到需要带什么？",
        answer="新生报到需要携带录取通知书和有效身份证件。[S1]",
        sources=[source],
        origin=AnswerOrigin.KNOWLEDGE_BASE,
    )
    second_message = create_answer_message(
        user_id,
        question="新生报到需要带什么",
        answer="请携带录取通知书和身份证件。[S1]",
        sources=[source],
        origin=AnswerOrigin.KNOWLEDGE_BASE,
    )

    first = run_task(user_id, first_message)
    second = run_task(user_id, second_message)

    assert first.status == AnswerKnowledgeStatus.COMPLETE
    assert first.qa_entry_id is not None
    assert second.qa_entry_id == first.qa_entry_id
    assert first.document_id is None
    with SessionLocal() as db:
        assert db.scalar(select(func.count(QaEntry.id))) == 1
        assert db.scalar(select(func.count(QaSourceLink.id))) == 1
        assert db.scalar(select(func.count(Document.id))) == 1

    monkeypatch.setattr(settings, "qa_retrieval_enabled", True)
    lookup = qa_knowledge_service.lookup("新生报到需要带什么？")
    assert lookup.mode == "direct"
    assert lookup.match is not None
    visible_sources = [item.source_dict() for item in lookup.sources]
    assert [item["document_id"] for item in visible_sources] == [document_id]
    assert all(item["title"] != "新生报到材料" for item in visible_sources)


def test_web_sources_are_archived_separately_and_deduplicated(monkeypatch) -> None:
    monkeypatch.setattr(answer_knowledge_service, "submit", lambda _task_id: None)
    monkeypatch.setattr(embedding.embedder, "embed_documents", fake_vectors)
    monkeypatch.setattr(embedding.embedder, "embed_query", lambda _text: fake_vectors([""])[0])
    clean_calls = 0

    def clean(**_kwargs) -> str:  # type: ignore[no-untyped-def]
        nonlocal clean_calls
        clean_calls += 1
        return (
            "# 河海大学本科招生规模\n\n"
            "## 标准问题\n河海大学每年本科招生多少人？\n\n"
            "## 标准答案\n2025年录取本科新生5758人。[W1]"
        )

    monkeypatch.setattr(
        "app.services.answer_knowledge.generator.clean_answer_for_knowledge", clean
    )
    user_id = create_user()
    web_source = {
        "source_type": "WEB_SEARCH",
        "citation_index": 1,
        "title": "河海大学招生信息",
        "url": "https://zsw.hhu.edu.cn/plan#section",
        "snippet": "2025年录取本科新生5758人。",
        "content": "河海大学2025年录取本科新生5758人。",
    }
    messages = [
        create_answer_message(
            user_id,
            question="河海大学每年招生多少人？",
            answer="2025年录取本科新生5758人。[W1]",
            sources=[web_source],
            origin=AnswerOrigin.WEB_SEARCH,
        )
        for _ in range(2)
    ]

    tasks = [run_task(user_id, message_id) for message_id in messages]

    assert tasks[0].qa_entry_id == tasks[1].qa_entry_id
    assert clean_calls == 1
    with SessionLocal() as db:
        documents = db.scalars(select(Document)).all()
        assert len(documents) == 1
        assert documents[0].category == settings.answer_web_archive_category
        assert documents[0].source_url == "https://zsw.hhu.edu.cn/plan"
        assert db.scalar(select(func.count(QaSourceLink.id))) == 1

    monkeypatch.setattr(settings, "qa_retrieval_enabled", True)
    lookup = qa_knowledge_service.lookup("河海大学每年本科招生多少人？")
    assert lookup.mode == "direct"
    assert lookup.sources[0].marker == "S"
    assert lookup.sources[0].original_marker == "W"
    assert lookup.sources[0].source_dict()["source_type"] == "WEB_ARCHIVE"
