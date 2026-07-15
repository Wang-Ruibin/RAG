"""文档相关 Pydantic 模型"""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """文档创建请求"""
    title: str = Field(..., max_length=255, description="文档标题")
    content: str | None = Field(None, description="文档内容")
    category: str | None = Field(None, max_length=50, description="分类")
    department: str | None = Field(None, max_length=100, description="所属部门")
    file_type: str | None = Field(None, max_length=20, description="文件类型")
    file_path: str | None = Field(None, max_length=500, description="文件路径")
    source_url: str | None = Field(None, max_length=500, description="来源URL")
    tags: list[str] | None = Field(None, description="标签数组")
    status: int = Field(1, description="状态: 0=草稿,1=已发布,2=已归档")


class DocumentUpdate(BaseModel):
    """文档更新请求"""
    title: str | None = None
    content: str | None = None
    category: str | None = None
    department: str | None = None
    file_type: str | None = None
    file_path: str | None = None
    source_url: str | None = None
    tags: list[str] | None = None
    chunk_count: int | None = None
    status: int | None = None


class DocumentResponse(BaseModel):
    """文档信息响应"""
    id: int
    title: str
    content: str | None
    category: str | None
    department: str | None
    file_type: str | None
    file_path: str | None
    source_url: str | None
    tags: list | None
    chunk_count: int
    status: int
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    """文档列表响应"""
    total: int
    items: list[DocumentResponse]
    page: int
    page_size: int
