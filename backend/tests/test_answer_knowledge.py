from __future__ import annotations

import numpy as np
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import AnswerKnowledgeStatus, AnswerOrigin, MessageRole, MessageStatus, Role
from app.models.orm import AnswerKnowledgeTask, Conversation, Document, Message, User
from app.rag import embedding
from app.rag.index import index_manager
from app.services.answer_knowledge import answer_knowledge_service


def test_answer_knowledge_task_cleans_and_hot_adds_document(monkeypatch) -> None:
    with SessionLocal() as db:
        user = User(
            name="满意回答用户",
            email="answer-kb@example.com",
            password_hash=hash_password("safe-pass-123"),
            role=Role.STUDENT,
        )
        db.add(user)
        db.flush()
        conversation = Conversation(user_id=user.id, title="校历问题")
        db.add(conversation)
        db.flush()
        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="新生报到需要带什么？",
                status=MessageStatus.COMPLETE,
            )
        )
        assistant = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="好的，同学你好！新生报到需要携带录取通知书和有效身份证件。[S1]",
            sources_json=[
                {
                    "source_type": "KNOWLEDGE_BASE",
                    "citation_index": 1,
                    "title": "新生报到指南",
                    "snippet": "新生报到需要携带录取通知书和有效身份证件。",
                }
            ],
            status=MessageStatus.COMPLETE,
            answer_origin=AnswerOrigin.KNOWLEDGE_BASE,
        )
        db.add(assistant)
        db.commit()
        db.refresh(user)
        db.refresh(assistant)
        user_id = user.id
        assistant_id = assistant.id

    monkeypatch.setattr(answer_knowledge_service, "submit", lambda _task_id: None)
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        task = answer_knowledge_service.create_task(db, user, assistant_id)
        task_id = task.id

    monkeypatch.setattr(
        "app.services.answer_knowledge.generator.clean_answer_for_knowledge",
        lambda **_kwargs: (
            "# 新生报到材料\n\n"
            "## 适用问题\n新生报到需要准备哪些材料。\n\n"
            "## 知识条目\n新生报到应携带录取通知书和有效身份证件。\n\n"
            "## 来源依据\n[S1] 新生报到指南。"
        ),
    )

    def fake_embeddings(texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 8), dtype=np.float32)
        vectors[:, 0] = 1.0
        return vectors

    monkeypatch.setattr(embedding.embedder, "embed_documents", fake_embeddings)

    answer_knowledge_service.process(task_id)

    with SessionLocal() as db:
        task = db.get(AnswerKnowledgeTask, task_id)
        assert task is not None
        assert task.status == AnswerKnowledgeStatus.COMPLETE
        assert task.document_id is not None
        assert task.cleaned_title == "新生报到材料"
        assert "同学你好" not in (task.cleaned_content or "")
        document = db.get(Document, task.document_id)
        assert document is not None
        assert document.status.name == "READY"
        assert document.category == "问答沉淀"
        assert document.chunk_count > 0
        assert index_manager.count == document.chunk_count
