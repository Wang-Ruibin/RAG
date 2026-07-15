from enum import StrEnum


class Role(StrEnum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"


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
