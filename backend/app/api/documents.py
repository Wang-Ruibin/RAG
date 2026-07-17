from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.responses import success
from app.models.enums import DocumentStatus
from app.models.orm import Document
from app.models.schemas import DocumentOut, DocumentPreviewOut, DocumentUpdateRequest
from app.services.documents import DuplicateDocumentError, document_service

from .dependencies import AdminUser, CurrentUser, Database

router = APIRouter(prefix="/api/documents", tags=["知识库"])


def serialize(document: Document) -> dict[str, object]:
    return DocumentOut.model_validate(document).model_dump(mode="json")


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    db: Database,
    admin: AdminUser,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "其他",
) -> dict[str, object]:
    original_name = Path((file.filename or "").replace("\\", "/")).name
    suffix = Path(original_name).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="仅支持 Markdown、TXT、PDF、DOCX 文件")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件不能超过 50MB")
    try:
        document, job = document_service.save_upload(
            db,
            data=data,
            original_name=original_name,
            mime_type=file.content_type or "application/octet-stream",
            title=title or Path(original_name).stem,
            category=category,
            uploaded_by=admin.id,
        )
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success(
        {"document": serialize(document), "job_id": job.id},
        "上传成功，已进入后台处理队列",
        202,
    )


@router.get("")
def list_documents(
    db: Database,
    _user: CurrentUser,
    page: int = 1,
    size: int = 20,
    q: str = "",
    status_filter: DocumentStatus | None = None,
    category: str = "",
) -> dict[str, object]:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    filters = []
    if q:
        filters.append(Document.title.contains(q))
    if status_filter:
        filters.append(Document.status == status_filter)
    if category:
        filters.append(Document.category == category)
    total = db.scalar(select(func.count(Document.id)).where(*filters)) or 0
    documents = db.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return success(
        {
            "items": [serialize(document) for document in documents],
            "total": total,
            "page": page,
            "size": size,
        }
    )


@router.get("/{document_id}")
def get_document(document_id: int, db: Database, _user: CurrentUser) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success(serialize(document))


@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    db: Database,
    _user: CurrentUser,
    offset: int = 0,
    limit: int = 20_000,
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    offset = max(0, offset)
    limit = min(max(1, limit), 50_000)
    try:
        text, preview_format = document_service.preview_text(document)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"文档预览失败: {exc}") from exc
    total = len(text)
    payload = DocumentPreviewOut(
        content=text[offset : offset + limit],
        offset=offset,
        limit=limit,
        total_chars=total,
        has_more=offset + limit < total,
        format=preview_format,
    )
    return success(payload.model_dump(mode="json"))


@router.get("/{document_id}/download")
def download_document(document_id: int, db: Database, _user: CurrentUser) -> FileResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        path = document_service.source_path(document)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=document.mime_type, filename=document.original_name)


@router.patch("/{document_id}")
def update_document(
    document_id: int,
    payload: DocumentUpdateRequest,
    db: Database,
    _admin: AdminUser,
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status in {DocumentStatus.QUEUED, DocumentStatus.PROCESSING}:
        raise HTTPException(status_code=409, detail="文档处理期间不能修改")
    if payload.source_url and not payload.source_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="来源链接必须使用 http 或 https")
    try:
        updated = document_service.update_metadata(
            db,
            document,
            title=payload.title,
            category=payload.category,
            source_url=payload.source_url,
            published_at=payload.published_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success(serialize(updated), "知识库资料已更新")


@router.post("/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_document(document_id: int, db: Database, _admin: AdminUser) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status in {DocumentStatus.QUEUED, DocumentStatus.PROCESSING}:
        raise HTTPException(status_code=409, detail="文档正在处理中")
    job = document_service.enqueue_reprocess(db, document)
    return success({"document_id": document_id, "job_id": job.id}, "已进入重新处理队列", 202)


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Database, _admin: AdminUser) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    document_service.delete_document(db, document)
    return success(None, "文档、文本块、向量和原文件已删除")
