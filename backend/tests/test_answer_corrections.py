from __future__ import annotations

import numpy as np
import pytest
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.enums import (
    AnswerCorrectionStatus,
    AnswerOrigin,
    DocumentKind,
    DocumentStatus,
    MessageRole,
    MessageStatus,
    Role,
)
from app.models.orm import (
    AnswerCorrection,
    Conversation,
    CorrectionSourceLink,
    Document,
    Message,
    QaEntry,
    User,
)
from app.rag import embedding
from app.rag.index import index_manager
from app.rag.retrieval import retrieval_service
from app.services.answer_corrections import answer_correction_service
from app.services.documents import document_service
from httpx import AsyncClient
from sqlalchemy import func, select

pytestmark = pytest.mark.anyio


def fake_vectors(texts: list[str]) -> np.ndarray:
    vectors = np.zeros((len(texts), 8), dtype=np.float32)
    vectors[:, 0] = 1.0
    return vectors


def create_admin() -> tuple[int, dict[str, str]]:
    with SessionLocal() as db:
        admin = User(
            name="审核管理员",
            email="correction-admin@example.com",
            password_hash=hash_password("admin-pass-123"),
            role=Role.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin.id, {
            "Authorization": f"Bearer {create_access_token(admin.id, admin.role.value)}"
        }


async def register_user(client: AsyncClient, email: str) -> tuple[int, dict[str, str]]:
    response = await client.post(
        "/api/auth/register",
        json={"name": "知识提供者", "email": email, "password": "safe-pass-123"},
    )
    data = response.json()["data"]
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


def create_answer(user_id: int) -> tuple[int, int]:
    with SessionLocal() as db:
        conversation = Conversation(user_id=user_id, title="河海大学校训")
        db.add(conversation)
        db.flush()
        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="河海大学的校训是什么？",
                status=MessageStatus.COMPLETE,
            )
        )
        assistant = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="暂未找到答案。",
            sources_json=[],
            status=MessageStatus.COMPLETE,
            answer_origin=AnswerOrigin.NO_ANSWER,
        )
        db.add(assistant)
        db.commit()
        return conversation.id, assistant.id


def create_ready_source(admin_id: int) -> int:
    with SessionLocal() as db:
        document, _job = document_service.save_upload(
            db,
            data=b"# Hohai University\n\nReference document.",
            original_name="reference.md",
            mime_type="text/markdown",
            title="河海大学参考资料",
            category="校情",
            uploaded_by=admin_id,
            enqueue=False,
        )
        document.status = DocumentStatus.READY
        db.commit()
        return document.id


async def test_correction_ownership_reject_resubmit_and_approval_pipeline(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(answer_correction_service, "submit", lambda _correction_id: None)
    monkeypatch.setattr(embedding.embedder, "embed_documents", fake_vectors)
    monkeypatch.setattr(embedding.embedder, "embed_query", lambda _text: fake_vectors([""])[0])
    admin_id, admin_header = create_admin()
    user_id, user_header = await register_user(client, "contributor@example.com")
    _other_id, other_header = await register_user(client, "other-contributor@example.com")
    conversation_id, assistant_id = create_answer(user_id)

    submitted = await client.post(
        f"/api/messages/{assistant_id}/correction",
        headers=user_header,
        json={"corrected_answer": "河海大学校训是艰苦朴素、实事求是、严格要求、勇于探索。"},
    )
    assert submitted.status_code == 202
    correction_id = submitted.json()["data"]["id"]
    duplicate = await client.post(
        f"/api/messages/{assistant_id}/correction",
        headers=user_header,
        json={"corrected_answer": "不应该覆盖待审答案"},
    )
    assert duplicate.json()["data"]["id"] == correction_id
    assert duplicate.json()["data"]["proposed_answer"].startswith("河海大学校训")
    forbidden = await client.post(
        f"/api/messages/{assistant_id}/correction",
        headers=other_header,
        json={"corrected_answer": "越权纠错答案"},
    )
    assert forbidden.status_code == 404

    listed = await client.get(
        "/api/admin/answer-corrections?status_filter=PENDING", headers=admin_header
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["contributor_email"] == "contributor@example.com"

    rejected = await client.post(
        f"/api/admin/answer-corrections/{correction_id}/reject",
        headers=admin_header,
        json={"reason": "请补充完整表述"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "REJECTED"
    history = await client.get(
        f"/api/conversations/{conversation_id}", headers=user_header
    )
    assistant = history.json()["data"]["messages"][1]
    assert assistant["correction"]["status"] == "REJECTED"
    assert assistant["correction"]["review_note"] == "请补充完整表述"

    resubmitted = await client.post(
        f"/api/messages/{assistant_id}/correction",
        headers=user_header,
        json={"corrected_answer": "河海大学校训：艰苦朴素、实事求是、严格要求、勇于探索。"},
    )
    assert resubmitted.json()["data"]["id"] == correction_id
    assert resubmitted.json()["data"]["status"] == "PENDING"
    source_document_id = create_ready_source(admin_id)

    approved = await client.post(
        f"/api/admin/answer-corrections/{correction_id}/approve",
        headers=admin_header,
        json={
            "question": "河海大学的校训是什么？",
            "answer": "河海大学校训是艰苦朴素、实事求是、严格要求、勇于探索。",
            "source_document_ids": [source_document_id],
        },
    )
    assert approved.status_code == 202
    assert approved.json()["data"]["status"] == "PROCESSING"
    answer_correction_service.process(correction_id)

    with SessionLocal() as db:
        correction = db.get(AnswerCorrection, correction_id)
        assert correction is not None
        assert correction.status == AnswerCorrectionStatus.APPROVED
        assert correction.approved_document_id is not None
        correction_document_id = correction.approved_document_id
        document = db.get(Document, correction_document_id)
        assert document is not None
        assert document.status == DocumentStatus.READY
        assert document.document_kind == DocumentKind.USER_CORRECTION
        assert document.contributor_name == "知识提供者"
        correction_markdown = (settings.upload_dir / document.stored_name).read_text(
            encoding="utf-8"
        )
        assert "河海大学参考资料" not in correction_markdown
        assert "审核状态：管理员已审核" in correction_markdown
        assert db.scalar(select(func.count(QaEntry.id))) == 0
        assert db.scalar(select(func.count(CorrectionSourceLink.id))) == 1

    matches = retrieval_service.search(
        "河海大学的校训是什么",
        top_k=5,
        use_rerank=False,
    )
    correction_match = next(item for item in matches if item.document_id == correction_document_id)
    assert correction_match.document_kind == "USER_CORRECTION"
    assert correction_match.contributor_name == "知识提供者"
    source = correction_match.source_dict(citation_index=1)
    source["source_type"] = correction_match.document_kind
    assert source["source_type"] == "USER_CORRECTION"
    assert source["contributor_name"] == "知识提供者"

    deleted = await client.delete(
        f"/api/documents/{correction_document_id}", headers=admin_header
    )
    assert deleted.status_code == 200
    assert all(
        record.document_id != correction_document_id
        for record in index_manager.snapshot().records.values()
    )


async def test_correction_rejects_non_ready_source_and_recovers_interrupted_status(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(answer_correction_service, "submit", lambda _correction_id: None)
    admin_id, admin_header = create_admin()
    user_id, user_header = await register_user(client, "recovery@example.com")
    _conversation_id, assistant_id = create_answer(user_id)
    submitted = await client.post(
        f"/api/messages/{assistant_id}/correction",
        headers=user_header,
        json={"corrected_answer": "这是用户提供的准确答案。"},
    )
    correction_id = submitted.json()["data"]["id"]
    with SessionLocal() as db:
        queued, _job = document_service.save_upload(
            db,
            data=b"queued source",
            original_name="queued.txt",
            mime_type="text/plain",
            title="未完成资料",
            category="测试",
            uploaded_by=admin_id,
            enqueue=False,
        )
        queued_id = queued.id
    invalid = await client.post(
        f"/api/admin/answer-corrections/{correction_id}/approve",
        headers=admin_header,
        json={
            "question": "审核问题",
            "answer": "审核答案",
            "source_document_ids": [queued_id],
        },
    )
    assert invalid.status_code == 400

    with SessionLocal() as db:
        correction = db.get(AnswerCorrection, correction_id)
        assert correction is not None
        correction.status = AnswerCorrectionStatus.PROCESSING
        db.commit()
    assert answer_correction_service.recover_stuck_corrections() == 1
    with SessionLocal() as db:
        correction = db.get(AnswerCorrection, correction_id)
        assert correction is not None
        assert correction.status == AnswerCorrectionStatus.FAILED
        assert "服务重启" in (correction.error or "")
