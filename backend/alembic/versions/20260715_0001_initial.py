"""Initial CampusQA schema.

This revision intentionally declares the historical schema instead of importing
the live ORM metadata. Otherwise a fresh install would create tables belonging
to later revisions before those revisions run.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260715_0001"
down_revision = None
branch_labels = None
depends_on = None


role_enum = sa.Enum("STUDENT", "ADMIN", name="role")
document_status_enum = sa.Enum(
    "QUEUED", "PROCESSING", "READY", "FAILED", "DELETING", name="documentstatus"
)
processing_stage_enum = sa.Enum(
    "SAVED",
    "EXTRACTING",
    "CLEANING",
    "CHUNKING",
    "EMBEDDING",
    "INDEXING",
    "COMPLETE",
    name="processingstage",
)
message_role_enum = sa.Enum("USER", "ASSISTANT", name="messagerole")
message_status_enum = sa.Enum(
    "STREAMING", "COMPLETE", "CANCELLED", "ERROR", name="messagestatus"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("original_name", sa.String(length=500), nullable=False),
        sa.Column("stored_name", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1200), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("stage", processing_stage_enum, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )
    for column in ("title", "category", "content_hash", "status", "uploaded_by"):
        op.create_index(f"ix_documents_{column}", "documents", [column], unique=False)

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("stage", processing_stage_enum, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"], unique=False
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("status", message_status_enum, nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("retrieval_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_messages_conversation_id", "messages", ["conversation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
    op.drop_table("users")
