"""文档业务服务"""

from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """文档服务"""

    @staticmethod
    def create(db: Session, data: DocumentCreate, user_id: int) -> Document:
        """创建文档"""
        document = Document(
            title=data.title,
            content=data.content,
            category=data.category,
            department=data.department,
            file_type=data.file_type,
            file_path=data.file_path,
            source_url=data.source_url,
            tags=data.tags,
            status=data.status,
            created_by=user_id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def get_by_id(db: Session, document_id: int) -> Document | None:
        """根据ID获取文档"""
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def update(db: Session, document_id: int, data: DocumentUpdate) -> Document | None:
        """更新文档"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(document, key, value)

        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def soft_delete(db: Session, document_id: int) -> bool:
        """软删除文档（将状态设为已归档）"""
        document = DocumentService.get_by_id(db, document_id)
        if not document:
            return False
        document.status = 2
        db.commit()
        return True

    @staticmethod
    def get_list(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        department: str | None = None,
        status: int | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Document], int]:
        """获取文档列表（分页 + 筛选）"""
        query = db.query(Document)

        if category:
            query = query.filter(Document.category == category)
        if department:
            query = query.filter(Document.department == department)
        if status is not None:
            query = query.filter(Document.status == status)
        else:
            query = query.filter(Document.status != 2)  # 默认排除已归档
        if keyword:
            like_pattern = f"%{keyword}%"
            query = query.filter(
                Document.title.ilike(like_pattern)
                | Document.content.ilike(like_pattern)
            )

        total = query.count()
        documents = (
            query.order_by(Document.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return documents, total

    @staticmethod
    def get_categories(db: Session) -> list[str]:
        """获取所有文档分类"""
        results = (
            db.query(Document.category)
            .filter(Document.category.isnot(None), Document.status == 1)
            .distinct()
            .all()
        )
        return [r[0] for r in results if r[0]]
