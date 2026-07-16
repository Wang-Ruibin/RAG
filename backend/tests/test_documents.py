from __future__ import annotations

import numpy as np
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.enums import DocumentStatus, ProcessingStage, Role
from app.models.orm import Document, User
from app.rag import embedding
from app.rag.index import IndexManager, index_manager
from app.services.documents import document_service


def test_document_ingestion_builds_rebuildable_index_and_delete_removes_it(
    monkeypatch,
) -> None:
    with SessionLocal() as db:
        admin = User(
            name="知识库管理员",
            email="kb-admin@example.com",
            password_hash=hash_password("admin-pass-123"),
            role=Role.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        document, job = document_service.save_upload(
            db,
            data=(
                "# 校园卡补办指南\n\n"
                "> 来源：https://example.edu.cn/card\n"
                "发布时间：2026-01-01\n\n"
                "## 办理材料\n\n校园卡补办需要携带有效身份证件。"
            ).encode(),
            original_name="../../card.md",
            mime_type="text/markdown",
            title="校园卡补办指南",
            category="campus_life",
            uploaded_by=admin.id,
            enqueue=False,
        )
        document_id = document.id
        job_id = job.id
        stored_name = document.stored_name

    def fake_embeddings(texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), 8), dtype=np.float32)
        vectors[:, 0] = 1.0
        return vectors

    monkeypatch.setattr(embedding.embedder, "embed_documents", fake_embeddings)
    document_service.process(document_id, job_id, rebuild=True)

    with SessionLocal() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.status == DocumentStatus.READY
        assert document.stage == ProcessingStage.COMPLETE
        assert document.original_name == "card.md"
        assert document.source_url == "https://example.edu.cn/card"
        assert document.chunk_count > 0
        assert index_manager.count == document.chunk_count
        first_id = index_manager.stable_chunk_id(document_id, 0)
        assert index_manager.dense_search(np.array([1.0] + [0.0] * 7), 5)[0][0] == first_id
        record = index_manager.records([first_id])[first_id]
        assert record.content.startswith("校园卡补办指南")
        assert record.source_url == "https://example.edu.cn/card"
        assert index_manager.artifact_path(document_id).exists()
        loaded = IndexManager()
        assert loaded.load() == document.chunk_count
        assert loaded.dense_search(np.array([1.0] + [0.0] * 7), 5)[0][0] == first_id
        document_service.update_metadata(
            db,
            document,
            title="校园卡补办新指南",
            category="办事服务",
            source_url="https://example.edu.cn/card-new",
            published_at=document.published_at,
        )
        assert index_manager.records([first_id])[first_id].title == "校园卡补办新指南"
        (settings.index_dir / "faiss.index").write_bytes(b"deliberately-corrupted")
        recovered = IndexManager()
        assert recovered.rebuild() == document.chunk_count
        assert recovered.records([first_id])[first_id].content == record.content
        document_service.delete_document(db, document)

    with SessionLocal() as db:
        assert db.get(Document, document_id) is None
    assert index_manager.count == 0
    assert not index_manager.artifact_path(document_id).exists()
    assert not (settings.upload_dir / stored_name).exists()


def test_business_database_has_no_knowledge_chunk_table() -> None:
    from app.core.database import Base

    assert "chunks" not in Base.metadata.tables
