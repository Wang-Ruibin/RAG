"""问答记录相关 Pydantic 模型"""

from datetime import datetime
from pydantic import BaseModel, Field


class QARecordCreate(BaseModel):
    """问答记录创建请求"""
    user_id: int = Field(..., description="用户ID")
    session_id: str | None = Field(None, max_length=100, description="会话ID")
    question: str = Field(..., description="用户问题")
    answer: str | None = Field(None, description="AI回答")
    sources: list[dict] | None = Field(None, description="文档来源列表")
    tokens_used: int = Field(0, description="消耗token数")
    duration_ms: int | None = Field(None, description="响应耗时(毫秒)")


class QARecordResponse(BaseModel):
    """问答记录响应"""
    id: int
    user_id: int
    session_id: str | None
    question: str
    answer: str | None
    sources: list | None
    tokens_used: int
    feedback: int
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnswerCreate(BaseModel):
    """AI回答保存请求"""
    record_id: int = Field(..., description="问答记录ID")
    answer: str = Field(..., description="AI回答")
    sources: list[dict] | None = Field(None, description="引用来源")
    tokens_used: int = Field(0, description="消耗token数")
    duration_ms: int | None = Field(None, description="响应耗时")


class QARecordList(BaseModel):
    """问答记录列表响应"""
    total: int
    items: list[QARecordResponse]
    page: int
    page_size: int
