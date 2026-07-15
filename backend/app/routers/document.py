"""文档管理 API 路由"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document_service import DocumentService
from app.services.user_service import UserService
from app.routers.user import _get_current_user

router = APIRouter(prefix="/api/document", tags=["文档管理"])


def _success(data=None, message="success"):
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


@router.post("")
def create_document(
    data: DocumentCreate,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """创建文档"""
    doc = DocumentService.create(db, data, user_id)
    return _success(
        data=DocumentResponse.model_validate(doc).model_dump(),
        message="文档创建成功",
    )


@router.get("/list")
def get_document_list(
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    department: str | None = None,
    status: int | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    """文档列表（分页、筛选）"""
    docs, total = DocumentService.get_list(
        db,
        page=page,
        page_size=page_size,
        category=category,
        department=department,
        status=status,
        keyword=keyword,
    )
    return _success(
        data={
            "total": total,
            "items": [DocumentResponse.model_validate(d).model_dump() for d in docs],
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取文档分类列表"""
    categories = DocumentService.get_categories(db)
    return _success(data={"categories": categories})


@router.get("/{document_id}")
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """获取文档详情"""
    doc = DocumentService.get_by_id(db, document_id)
    if not doc or doc.status == 2:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _success(data=DocumentResponse.model_validate(doc).model_dump())


@router.put("/{document_id}")
def update_document(
    document_id: int,
    data: DocumentUpdate,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """更新文档"""
    doc = DocumentService.update(db, document_id, data)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _success(
        data=DocumentResponse.model_validate(doc).model_dump(),
        message="文档更新成功",
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    user_id: int = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    """删除文档（软删除）"""
    # 验证权限（仅创建者或管理员可删除）
    current_user = UserService.get_by_id(db, user_id)
    doc = DocumentService.get_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.created_by != user_id and (not current_user or current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="无权限删除此文档")

    success = DocumentService.soft_delete(db, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _success(message="文档已删除")
