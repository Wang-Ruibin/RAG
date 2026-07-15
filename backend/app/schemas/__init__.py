"""Pydantic 请求/响应模型"""

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentList,
)
from app.schemas.qa_record import (
    AnswerCreate,
    QARecordCreate,
    QARecordResponse,
    QARecordList,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "Token",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "DocumentList",
    "AnswerCreate",
    "QARecordCreate",
    "QARecordResponse",
    "QARecordList",
]
