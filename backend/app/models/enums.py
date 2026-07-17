from enum import StrEnum


class Role(StrEnum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


class DocumentKind(StrEnum):
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    WEB_ARCHIVE = "WEB_ARCHIVE"
    USER_CORRECTION = "USER_CORRECTION"


class DocumentStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


class ProcessingStage(StrEnum):
    SAVED = "SAVED"
    EXTRACTING = "EXTRACTING"
    CLEANING = "CLEANING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    COMPLETE = "COMPLETE"


class MessageStatus(StrEnum):
    STREAMING = "STREAMING"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class MessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class AnswerOrigin(StrEnum):
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    WEB_SEARCH = "WEB_SEARCH"
    HYBRID = "HYBRID"
    NO_ANSWER = "NO_ANSWER"


class AnswerKnowledgeStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class AnswerCorrectionStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
