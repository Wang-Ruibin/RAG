"""Add answer origin and answer knowledge tasks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260716_0002"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


answer_origin_enum = sa.Enum(
    "KNOWLEDGE_BASE",
    "WEB_SEARCH",
    "NO_ANSWER",
    name="answerorigin",
)
answer_knowledge_status_enum = sa.Enum(
    "QUEUED",
    "PROCESSING",
    "COMPLETE",
    "FAILED",
    name="answerknowledgestatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "messages" in tables:
        message_columns = {column["name"] for column in inspector.get_columns("messages")}
        message_indexes = {index["name"] for index in inspector.get_indexes("messages")}
        if "answer_origin" not in message_columns:
            op.add_column(
                "messages",
                sa.Column("answer_origin", answer_origin_enum, nullable=True),
            )
        if "ix_messages_answer_origin" not in message_indexes:
            op.create_index(
                "ix_messages_answer_origin",
                "messages",
                ["answer_origin"],
                unique=False,
            )

    required_tables = {"users", "conversations", "messages", "documents"}
    if "answer_knowledge_tasks" not in tables and required_tables.issubset(tables):
        op.create_table(
            "answer_knowledge_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("conversation_id", sa.Integer(), nullable=False),
            sa.Column("assistant_message_id", sa.Integer(), nullable=False),
            sa.Column("source_answer_origin", answer_origin_enum, nullable=True),
            sa.Column("original_question", sa.Text(), nullable=False),
            sa.Column("original_answer", sa.Text(), nullable=False),
            sa.Column("sources_snapshot", sa.JSON(), nullable=False),
            sa.Column("cleaned_title", sa.String(length=300), nullable=True),
            sa.Column("cleaned_content", sa.Text(), nullable=True),
            sa.Column("document_id", sa.Integer(), nullable=True),
            sa.Column("status", answer_knowledge_status_enum, nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["assistant_message_id"], ["messages.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_answer_knowledge_tasks_assistant_message_id",
            "answer_knowledge_tasks",
            ["assistant_message_id"],
            unique=True,
        )
        for column in ("conversation_id", "document_id", "status", "user_id"):
            op.create_index(
                f"ix_answer_knowledge_tasks_{column}",
                "answer_knowledge_tasks",
                [column],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "answer_knowledge_tasks" in tables:
        op.drop_table("answer_knowledge_tasks")

    if "messages" in tables:
        message_columns = {column["name"] for column in inspector.get_columns("messages")}
        message_indexes = {index["name"] for index in inspector.get_indexes("messages")}
        if "answer_origin" in message_columns:
            with op.batch_alter_table("messages") as batch_op:
                if "ix_messages_answer_origin" in message_indexes:
                    batch_op.drop_index("ix_messages_answer_origin")
                batch_op.drop_column("answer_origin")
