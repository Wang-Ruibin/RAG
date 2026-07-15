"""
CampusQA — 校园知识问答助手 ORM 模型

在现有 RAG NoteBook ORM 模型基础上增量扩展，
所有模型继承同一 Base，确保可共用 Alembic 迁移。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Integer, BigInteger, String,
    Date, DateTime, Enum, Numeric,
    Boolean, JSON, ForeignKey,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    relationship,
)

# ──────────────────────────────────────────────
# 声明基类（与现有 RAG NoteBook 共用）
# ──────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# 2. 用户（多角色）
# ──────────────────────────────────────────────


class User(Base):
    """用户表 — 学生 / 教师 / 管理员"""

    __tablename__ = "users"
    __table_args__ = {"comment": "用户表（学生/教师/管理员）"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="登录账号（学号/工号）"
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="真实姓名")
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, comment="邮箱")
    phone: Mapped[Optional[str]] = mapped_column(String(20), comment="手机号")
    role: Mapped[str] = mapped_column(
        Enum("student", "teacher", "admin", name="user_role"),
        nullable=False, default="student",
        comment="角色: student=学生, teacher=教师, admin=管理员",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), comment="头像地址")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="最后登录时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan",
    )

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


# ──────────────────────────────────────────────
# 3. 校园知识库文档
# ──────────────────────────────────────────────


class CampusDocument(Base):
    """校园知识库文档 — 校园概况 / 规章制度 / 办事流程 / 校园资讯"""

    __tablename__ = "campus_documents"
    __table_args__ = {"comment": "校园知识库文档"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="文档标题")
    content: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False, comment="文档内容 (Markdown)")
    category: Mapped[str] = mapped_column(
        Enum("campus_info", "policy", "flow", "news", "general", name="doc_category"),
        nullable=False,
        comment="文档分类",
    )
    tags: Mapped[Optional[list]] = mapped_column(JSON, comment="标签数组")
    valid_from: Mapped[Optional[date]] = mapped_column(Date, comment="生效日期")
    valid_until: Mapped[Optional[date]] = mapped_column(Date, comment="失效日期")
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="访问次数")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        comment="创建者",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    creator: Mapped[Optional["User"]] = relationship("User")

    # ── 工具方法 ──
    def is_valid_now(self) -> bool:
        """判断文档当前是否在有效期内"""
        today = date.today()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        return True

    def increment_view_count(self) -> None:
        """递增访问计数（调用方负责 commit）"""
        self.view_count = (self.view_count or 0) + 1



# ──────────────────────────────────────────────
# 10. 对话会话
# ──────────────────────────────────────────────


class Conversation(Base):
    """对话会话 — 持久化对话历史"""

    __tablename__ = "conversations"
    __table_args__ = {"comment": "对话会话表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, comment="用户 ID",
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), comment="会话标题（自动生成）")
    context: Mapped[Optional[dict]] = mapped_column(
        JSON, comment="上下文状态（当前课程/部门等）"
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0, comment="消息总数")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


# ──────────────────────────────────────────────
# 11. 消息
# ──────────────────────────────────────────────


class Message(Base):
    """对话消息 — 单条对话记录"""

    __tablename__ = "messages"
    __table_args__ = {"comment": "对话消息表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, comment="所属会话",
    )
    role: Mapped[str] = mapped_column(
        Enum("user", "assistant", "system", name="message_role"),
        nullable=False, comment="消息角色",
    )
    content: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False, comment="消息内容")
    msg_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, comment="元数据（意图/来源/耗时）"
    )
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, comment="消耗 token 数")
    feedback_score: Mapped[Optional[int]] = mapped_column(
        Integer, comment="用户反馈 (-1/0/1)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # ── 关系 ──
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )


# ──────────────────────────────────────────────
# 12. 文档访问日志
# ──────────────────────────────────────────────


class DocumentAccessLog(Base):
    """知识库文档访问日志 — 用于统计和 RAG 调优"""

    __tablename__ = "document_access_logs"
    __table_args__ = {"comment": "文档访问日志"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment="被访问的文档 ID"
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer, comment="访问者 ID")
    query_text: Mapped[Optional[str]] = mapped_column(String(500), comment="用户查询文本")
    intent_type: Mapped[Optional[str]] = mapped_column(String(50), comment="意图类型")
    source: Mapped[str] = mapped_column(
        Enum("agent", "direct_retrieval", "faq_match", name="log_source"),
        nullable=False, default="agent",
        comment="访问来源",
    )
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, comment="检索耗时（毫秒）")
    score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), comment="检索分数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )




# ──────────────────────────────────────────────
# 导出统一列表，方便 Alembic 或迁移脚本遍历
# ──────────────────────────────────────────────

ALL_CAMPUS_MODELS = [
    User,
    CampusDocument,
    Conversation,
    Message,
    DocumentAccessLog,
]
