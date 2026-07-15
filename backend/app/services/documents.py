from __future__ import annotations

import hashlib
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.enums import DocumentStatus, ProcessingStage
from app.models.orm import Document, IngestionJob
from app.rag import embedding
from app.rag.chunker import chunk_document
from app.rag.index import index_manager
from app.rag.parser import parse_file


def utc_now() -> datetime:
    return datetime.now(UTC)


class DuplicateDocumentError(ValueError):
    def __init__(self, document_id: int) -> None:
        super().__init__(f"相同内容已存在，文档 ID: {document_id}")
        self.document_id = document_id


class DocumentService:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")
        self._futures: set[Future[None]] = set()
        self._future_lock = threading.Lock()

    def save_upload(
        self,
        db: Session,
        *,
        data: bytes,
        original_name: str,
        mime_type: str,
        title: str,
        category: str,
        uploaded_by: int,
        enqueue: bool = True,
    ) -> tuple[Document, IngestionJob]:
        suffix = Path(original_name).suffix.lower()
        if suffix not in settings.allowed_extensions:
            raise ValueError("仅支持 Markdown、TXT、PDF、DOCX 文件")
        if len(data) > settings.max_upload_bytes:
            raise ValueError("文件不能超过 50MB")
        digest = hashlib.sha256(data).hexdigest()
        existing = db.scalar(
            select(Document).where(
                Document.content_hash == digest,
                Document.status != DocumentStatus.DELETING,
            )
        )
        if existing is not None:
            raise DuplicateDocumentError(existing.id)

        stored_name = f"{uuid.uuid4().hex}{suffix}"
        target = settings.upload_dir / stored_name
        target.write_bytes(data)
        document = Document(
            title=title.strip() or Path(original_name).stem,
            original_name=Path(original_name).name,
            stored_name=stored_name,
            mime_type=mime_type,
            size=len(data),
            category=category.strip() or "其他",
            content_hash=digest,
            uploaded_by=uploaded_by,
            status=DocumentStatus.QUEUED,
            stage=ProcessingStage.SAVED,
        )
        db.add(document)
        db.flush()
        job = IngestionJob(document_id=document.id)
        db.add(job)
        db.commit()
        db.refresh(document)
        db.refresh(job)
        if enqueue:
            self.submit(document.id, job.id)
        return document, job

    def import_path(
        self,
        path: Path,
        *,
        uploaded_by: int,
        category: str,
        rebuild: bool = False,
    ) -> Document | None:
        data = path.read_bytes()
        with SessionLocal() as db:
            try:
                document, job = self.save_upload(
                    db,
                    data=data,
                    original_name=path.name,
                    mime_type="text/markdown" if path.suffix.lower() == ".md" else "text/plain",
                    title=path.stem,
                    category=category,
                    uploaded_by=uploaded_by,
                    enqueue=False,
                )
            except DuplicateDocumentError:
                return None
        self.process(document.id, job.id, rebuild=rebuild)
        return document

    def submit(self, document_id: int, job_id: int) -> None:
        future = self._executor.submit(self.process, document_id, job_id, True)
        with self._future_lock:
            self._futures.add(future)
        future.add_done_callback(self._discard_future)

    def _discard_future(self, future: Future[None]) -> None:
        with self._future_lock:
            self._futures.discard(future)

    def enqueue_reprocess(self, db: Session, document: Document) -> IngestionJob:
        document.status = DocumentStatus.QUEUED
        document.stage = ProcessingStage.SAVED
        document.error = None
        job = IngestionJob(document_id=document.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        self.submit(document.id, job.id)
        return job

    def process(self, document_id: int, job_id: int, rebuild: bool = True) -> None:
        try:
            self._set_stage(document_id, job_id, ProcessingStage.EXTRACTING, start=True)
            with SessionLocal() as db:
                document = db.get(Document, document_id)
                if document is None:
                    return
                path = settings.upload_dir / document.stored_name
            parsed = parse_file(path)

            self._set_stage(document_id, job_id, ProcessingStage.CLEANING)
            self._set_stage(document_id, job_id, ProcessingStage.CHUNKING)
            drafts = chunk_document(parsed)
            if not drafts:
                raise ValueError("文档没有可索引的正文，可能是扫描件或空文件")

            self._set_stage(document_id, job_id, ProcessingStage.EMBEDDING)
            vectors = embedding.embedder.embed_documents([draft.content for draft in drafts])
            if len(vectors) != len(drafts):
                raise RuntimeError("Embedding 返回数量与 chunk 数不一致")

            self._set_stage(document_id, job_id, ProcessingStage.INDEXING)
            with SessionLocal() as db:
                document = db.get(Document, document_id)
                if document is None:
                    return
                title = parsed.title or document.title
                source_url = parsed.source_url or document.source_url
                published_at = parsed.published_at or document.published_at
                category = document.category
                document.title = title
                document.source_url = source_url
                document.published_at = published_at
                document.chunk_count = len(drafts)
                document.status = DocumentStatus.PROCESSING
                document.stage = ProcessingStage.INDEXING
                db.commit()

            index_manager.upsert_document(
                document_id=document_id,
                title=title,
                category=category,
                source_url=source_url,
                published_at=published_at,
                drafts=drafts,
                vectors=vectors,
                embedding_model=settings.embedding_model,
                rebuild=rebuild,
            )
            self._finish(document_id, job_id)
        except Exception as exc:
            self._fail(document_id, job_id, exc)
            if rebuild:
                try:
                    index_manager.rebuild()
                except Exception:
                    pass

    def _set_stage(
        self,
        document_id: int,
        job_id: int,
        stage: ProcessingStage,
        *,
        start: bool = False,
    ) -> None:
        with SessionLocal() as db:
            document = db.get(Document, document_id)
            job = db.get(IngestionJob, job_id)
            if document is None or job is None:
                return
            document.status = DocumentStatus.PROCESSING
            document.stage = stage
            job.status = DocumentStatus.PROCESSING
            job.stage = stage
            if start:
                job.attempts += 1
                job.started_at = utc_now()
            db.commit()

    def _finish(self, document_id: int, job_id: int) -> None:
        with SessionLocal() as db:
            document = db.get(Document, document_id)
            job = db.get(IngestionJob, job_id)
            if document is None or job is None:
                return
            document.status = DocumentStatus.READY
            document.stage = ProcessingStage.COMPLETE
            document.error = None
            job.status = DocumentStatus.READY
            job.stage = ProcessingStage.COMPLETE
            job.finished_at = utc_now()
            job.error = None
            db.commit()

    def _fail(self, document_id: int, job_id: int, exc: Exception) -> None:
        message = f"{type(exc).__name__}: {exc}"[:4000]
        with SessionLocal() as db:
            document = db.get(Document, document_id)
            job = db.get(IngestionJob, job_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.error = message
            if job is not None:
                job.status = DocumentStatus.FAILED
                job.error = message
                job.finished_at = utc_now()
            db.commit()

    def delete_document(self, db: Session, document: Document) -> None:
        document.status = DocumentStatus.DELETING
        stored_name = document.stored_name
        db.commit()
        try:
            index_manager.delete_document(document.id)
            db.delete(document)
            db.commit()
        except Exception as exc:
            db.rollback()
            current = db.get(Document, document.id)
            if current is not None:
                current.status = DocumentStatus.FAILED
                current.error = f"删除知识库资料失败: {type(exc).__name__}: {exc}"[:4000]
                db.commit()
            raise
        path = settings.upload_dir / stored_name
        if path.exists():
            path.unlink()

    def update_metadata(
        self,
        db: Session,
        document: Document,
        *,
        title: str,
        category: str,
        source_url: str | None,
        published_at: date | None,
    ) -> Document:
        new_title = title.strip()
        new_category = category.strip()
        if not new_title or not new_category:
            raise ValueError("标题和分类不能为空")
        old = (document.title, document.category, document.source_url, document.published_at)
        document.title = new_title
        document.category = new_category
        document.source_url = source_url.strip() if source_url else None
        document.published_at = published_at
        try:
            if document.status == DocumentStatus.READY:
                updated = index_manager.update_document_metadata(
                    document.id,
                    title=document.title,
                    category=document.category,
                    source_url=document.source_url,
                    published_at=document.published_at,
                )
                if not updated:
                    raise RuntimeError("知识库资料文件不存在，请重新处理文档")
            db.commit()
            db.refresh(document)
            return document
        except Exception:
            document.title, document.category, document.source_url, document.published_at = old
            db.rollback()
            raise

    def recover_stuck_jobs(self) -> int:
        with SessionLocal() as db:
            documents = db.scalars(
                select(Document).where(Document.status == DocumentStatus.PROCESSING)
            ).all()
            for document in documents:
                document.status = DocumentStatus.FAILED
                document.error = "服务重启中断了文档处理，请点击重新处理"
            db.commit()
            return len(documents)


document_service = DocumentService()
