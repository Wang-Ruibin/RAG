"""
CampusQA — 校园知识问答助手 ORM 模型

在现有 RAG NoteBook ORM 模型基础上增量扩展，
所有模型继承同一 Base，确保可共用 Alembic 迁移。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Integer, BigInteger, String, Text,
    Date, DateTime, Enum, Numeric,
    Boolean, JSON, ForeignKey, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    relationship, validates,
)

# ──────────────────────────────────────────────
# 声明基类（与现有 RAG NoteBook 共用）
# ──────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# 1. 院系/部门
# ──────────────────────────────────────────────


class Department(Base):
    """院系/部门组织架构（树形结构，自引用 FK）"""

    __tablename__ = "departments"
    __table_args__ = {"comment": "院系/部门组织架构"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="部门名称")
    code: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, comment="部门代码（如 CS, MATH）"
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="上级部门 ID",
    )
    level: Mapped[int] = mapped_column(
        Integer, default=1, comment="层级: 1=学院, 2=系/所, 3=科室"
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="部门简介")
    phone: Mapped[Optional[str]] = mapped_column(String(30), comment="联系电话")
    location: Mapped[Optional[str]] = mapped_column(String(200), comment="办公地点")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    children: Mapped[list["Department"]] = relationship(
        "Department", back_populates="parent",
        cascade="all, delete-orphan",  # only applies to children added via this parent
    )
    parent: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="children", remote_side="Department.id",
    )

    # ── 工具方法 ──
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "level": self.level,
            "phone": self.phone,
            "location": self.location,
        }


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
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="所属院系",
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
    department: Mapped[Optional["Department"]] = relationship("Department")
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
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="所属部门",
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
    department: Mapped[Optional["Department"]] = relationship("Department")
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
# 4. 课程
# ──────────────────────────────────────────────


class Course(Base):
    """课程信息"""

    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code", "semester", name="uk_course_code_semester"),
        {"comment": "课程信息表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="课程代码（如 CS101）")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="课程名称")
    instructor: Mapped[str] = mapped_column(String(100), nullable=False, comment="授课教师")
    instructor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        comment="授课教师 user_id",
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="开课院系",
    )
    semester: Mapped[str] = mapped_column(String(20), nullable=False, comment="学期")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="课程简介")
    credits: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 1), comment="学分"
    )
    syllabus_path: Mapped[Optional[str]] = mapped_column(String(500), comment="教学大纲路径")
    max_students: Mapped[Optional[int]] = mapped_column(Integer, comment="容量上限")
    enrolled_count: Mapped[int] = mapped_column(Integer, default=0, comment="已选人数")
    status: Mapped[str] = mapped_column(
        Enum("upcoming", "active", "ended", "cancelled", name="course_status"),
        nullable=False, default="active",
        comment="课程状态",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    department: Mapped[Optional["Department"]] = relationship("Department")
    materials: Mapped[list["CourseMaterial"]] = relationship(
        "CourseMaterial", back_populates="course", cascade="all, delete-orphan",
    )

    @property
    def slots_available(self) -> int:
        """剩余名额"""
        if self.max_students is None:
            return -1  # 无限制
        return max(0, self.max_students - (self.enrolled_count or 0))


# ──────────────────────────────────────────────
# 5. 课程资料
# ──────────────────────────────────────────────


class CourseMaterial(Base):
    """课程资料文件 — 映射到 Chroma 向量集合"""

    __tablename__ = "course_materials"
    __table_args__ = {"comment": "课程资料文件"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False, comment="所属课程",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="资料标题")
    file_type: Mapped[str] = mapped_column(
        Enum("pdf", "pptx", "docx", "md", "txt", "image", name="file_type"),
        nullable=False, default="pdf",
        comment="文件类型",
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储路径")
    file_size: Mapped[int] = mapped_column(
        BigInteger, default=0, comment="文件大小（字节）"
    )
    chunk_status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "ready", "failed", name="chunk_status"),
        nullable=False, default="pending",
        comment="切片状态",
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="切片数量")
    md5: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, comment="文件 MD5 哈希"
    )
    uploaded_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, comment="上传者",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    course: Mapped["Course"] = relationship("Course", back_populates="materials")


# ──────────────────────────────────────────────
# 6. FAQ 问答对
# ──────────────────────────────────────────────


class FAQ(Base):
    """高频问答对 — 精确匹配 + 模糊语义匹配"""

    __tablename__ = "faq"
    __table_args__ = {"comment": "高频问答对"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String(300), nullable=False, comment="标准问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="标准答案")
    category: Mapped[Optional[str]] = mapped_column(String(50), comment="分类（教务/生活/就业/其他）")
    tags: Mapped[Optional[list]] = mapped_column(JSON, comment="标签数组")
    keywords: Mapped[Optional[list]] = mapped_column(JSON, comment="关键词数组")
    similar_questions: Mapped[Optional[list]] = mapped_column(JSON, comment="相似问法数组")
    related_faq_ids: Mapped[Optional[list]] = mapped_column(JSON, comment="关联 FAQ ID 列表")
    hit_count: Mapped[int] = mapped_column(Integer, default=0, comment="命中次数")
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级（高值优先）")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    def increment_hit_count(self) -> None:
        """递增命中次数（调用方负责 commit）"""
        self.hit_count = (self.hit_count or 0) + 1


# ──────────────────────────────────────────────
# 7. 校历事件
# ──────────────────────────────────────────────


class CalendarEvent(Base):
    """校历事件 — 学期安排 / 考试时间 / 节假日"""

    __tablename__ = "calendar_events"
    __table_args__ = {"comment": "校历事件表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="事件标题")
    event_type: Mapped[str] = mapped_column(
        Enum("semester", "exam", "holiday", "registration", "activity", "other",
             name="event_type"),
        nullable=False, default="other",
        comment="事件类型",
    )
    semester: Mapped[str] = mapped_column(String(20), nullable=False, comment="所属学期")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="开始日期")
    end_date: Mapped[date] = mapped_column(Date, nullable=False, comment="结束日期")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="事件描述")
    location: Mapped[Optional[str]] = mapped_column(String(200), comment="地点")
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否放假")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    @property
    def duration_days(self) -> int:
        """事件持续天数"""
        return (self.end_date - self.start_date).days + 1

    @validates("start_date", "end_date")
    def validate_dates(self, key: str, value: date) -> date:
        if key == "end_date" and self.start_date and value < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return value


# ──────────────────────────────────────────────
# 8. 办事流程
# ──────────────────────────────────────────────


class DocumentFlow(Base):
    """办事流程主表"""

    __tablename__ = "document_flows"
    __table_args__ = {"comment": "办事流程主表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="流程名称")
    flow_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="流程类型")
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="主管部门",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, comment="流程简介")
    total_steps: Mapped[int] = mapped_column(Integer, default=1, comment="总步骤数")
    estimated_time: Mapped[Optional[str]] = mapped_column(String(100), comment="预计办理时间")
    required_materials: Mapped[Optional[list]] = mapped_column(JSON, comment="所需材料清单")
    online_link: Mapped[Optional[str]] = mapped_column(String(500), comment="在线办理链接")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # ── 关系 ──
    department: Mapped[Optional["Department"]] = relationship("Department")
    steps: Mapped[list["FlowStep"]] = relationship(
        "FlowStep", back_populates="flow",
        cascade="all, delete-orphan",
        order_by="FlowStep.step_number",
    )


# ──────────────────────────────────────────────
# 9. 流程步骤
# ──────────────────────────────────────────────


class FlowStep(Base):
    """办事流程步骤明细"""

    __tablename__ = "flow_steps"
    __table_args__ = (
        UniqueConstraint("flow_id", "step_number", name="uk_flow_step"),
        {"comment": "办事流程步骤明细表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_flows.id", ondelete="CASCADE"),
        nullable=False, comment="所属流程",
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="步骤序号")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="步骤标题")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="步骤说明")
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"),
        comment="办理部门",
    )
    location: Mapped[Optional[str]] = mapped_column(String(200), comment="办理地点")
    phone: Mapped[Optional[str]] = mapped_column(String(30), comment="联系电话")
    online_url: Mapped[Optional[str]] = mapped_column(String(500), comment="在线办理链接")
    required_docs: Mapped[Optional[list]] = mapped_column(JSON, comment="所需材料")
    estimated_time: Mapped[Optional[str]] = mapped_column(String(100), comment="预计耗时")
    tips: Mapped[Optional[str]] = mapped_column(Text, comment="注意事项")
    condition_expr: Mapped[Optional[str]] = mapped_column(
        String(500), comment="条件表达式"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # ── 关系 ──
    flow: Mapped["DocumentFlow"] = relationship("DocumentFlow", back_populates="steps")


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
# 13. 系统配置
# ──────────────────────────────────────────────


class SystemConfig(Base):
    """系统动态配置"""

    __tablename__ = "system_configs"
    __table_args__ = {"comment": "系统动态配置表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="配置键"
    )
    config_value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="配置说明")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否对外可见")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


# ──────────────────────────────────────────────
# 导出统一列表，方便 Alembic 或迁移脚本遍历
# ──────────────────────────────────────────────

ALL_CAMPUS_MODELS = [
    Department,
    User,
    CampusDocument,
    Course,
    CourseMaterial,
    FAQ,
    CalendarEvent,
    DocumentFlow,
    FlowStep,
    Conversation,
    Message,
    DocumentAccessLog,
    SystemConfig,
]
