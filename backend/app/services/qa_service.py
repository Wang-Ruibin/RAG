"""问答记录业务服务"""

from sqlalchemy.orm import Session

from app.models.qa_record import QARecord
from app.schemas.qa_record import QARecordCreate


class QAService:
    """问答记录服务"""

    @staticmethod
    def create(db: Session, data: QARecordCreate) -> QARecord:
        """创建问答记录"""
        record = QARecord(
            user_id=data.user_id,
            session_id=data.session_id,
            question=data.question,
            answer=data.answer,
            sources=data.sources,
            tokens_used=data.tokens_used,
            duration_ms=data.duration_ms,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_by_id(db: Session, record_id: int) -> QARecord | None:
        """根据ID获取记录"""
        return db.query(QARecord).filter(QARecord.id == record_id).first()

    @staticmethod
    def get_session_history(
        db: Session,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QARecord], int]:
        """获取指定会话的历史记录"""
        query = (
            db.query(QARecord)
            .filter(QARecord.session_id == session_id)
        )
        total = query.count()
        records = (
            query.order_by(QARecord.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return records, total

    @staticmethod
    def get_user_history(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QARecord], int]:
        """获取用户的历史记录"""
        query = (
            db.query(QARecord)
            .filter(QARecord.user_id == user_id)
        )
        total = query.count()
        records = (
            query.order_by(QARecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return records, total

    @staticmethod
    def get_user_sessions(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取用户的所有会话列表（按session_id分组）"""
        from sqlalchemy import func as sa_func

        # 子查询：按 session_id 分组，取每个会话的最新时间和记录数
        subquery = (
            db.query(
                QARecord.session_id,
                sa_func.max(QARecord.created_at).label("last_time"),
                sa_func.count(QARecord.id).label("msg_count"),
                sa_func.min(QARecord.question).label("first_question"),
            )
            .filter(
                QARecord.user_id == user_id,
                QARecord.session_id.isnot(None),
            )
            .group_by(QARecord.session_id)
            .subquery()
        )

        # 查询所有分组并分页
        query = db.query(subquery)
        total = query.count()
        sessions = (
            query.order_by(subquery.c.last_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        result = []
        for s in sessions:
            result.append({
                "session_id": s[0],
                "last_time": s[1],
                "msg_count": s[2],
                "first_question": s[3],
            })
        return result, total

    @staticmethod
    def delete_session(db: Session, session_id: str, user_id: int | None = None) -> int:
        """删除指定会话的所有记录"""
        query = db.query(QARecord).filter(QARecord.session_id == session_id)
        if user_id is not None:
            query = query.filter(QARecord.user_id == user_id)
        deleted = query.delete(synchronize_session=False)
        db.commit()
        return deleted

    @staticmethod
    def update_feedback(
        db: Session, record_id: int, feedback: int
    ) -> QARecord | None:
        """更新问答反馈"""
        if feedback not in (0, 1, 2):
            raise ValueError("feedback 必须是 0(无)、1(有用) 或 2(无用)")

        record = QAService.get_by_id(db, record_id)
        if not record:
            return None

        record.feedback = feedback
        db.commit()
        db.refresh(record)
        return record
