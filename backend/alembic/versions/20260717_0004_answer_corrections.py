"""Add reviewed answer corrections and document provenance metadata."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0004"
down_revision = "20260717_0003"
branch_labels = None
depends_on = None


document_kind_enum = sa.Enum(
    "KNOWLEDGE_BASE",
    "WEB_ARCHIVE",
    "USER_CORRECTION",
    name="documentkind",
)
correction_status_enum = sa.Enum(
    "PENDING",
    "PROCESSING",
    "APPROVED",
    "REJECTED",
    "FAILED",
    name="answercorrectionstatus",
)


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "document_kind",
                document_kind_enum,
                server_default="KNOWLEDGE_BASE",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("contributor_name", sa.String(length=80), nullable=True))
        batch_op.create_index("ix_documents_document_kind", ["document_kind"], unique=False)
    op.execute("UPDATE documents SET document_kind='WEB_ARCHIVE' WHERE category='网页归档'")

    op.create_table(
        "answer_corrections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("assistant_message_id", sa.Integer(), nullable=True),
        sa.Column("contributor_name", sa.String(length=80), nullable=False),
        sa.Column("contributor_email", sa.String(length=255), nullable=False),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("original_answer", sa.Text(), nullable=False),
        sa.Column("original_sources", sa.JSON(), nullable=False),
        sa.Column("proposed_answer", sa.Text(), nullable=False),
        sa.Column("reviewed_question", sa.Text(), nullable=True),
        sa.Column("reviewed_answer", sa.Text(), nullable=True),
        sa.Column("status", correction_status_enum, nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("approved_document_id", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assistant_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assistant_message_id"),
    )
    for column in (
        "user_id",
        "conversation_id",
        "assistant_message_id",
        "status",
        "reviewed_by",
        "approved_document_id",
    ):
        op.create_index(
            f"ix_answer_corrections_{column}",
            "answer_corrections",
            [column],
            unique=column == "assistant_message_id",
        )

    op.create_table(
        "correction_source_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("correction_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["correction_id"], ["answer_corrections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correction_id", "document_id"),
    )
    op.create_index(
        "ix_correction_source_links_correction_id",
        "correction_source_links",
        ["correction_id"],
    )
    op.create_index(
        "ix_correction_source_links_document_id",
        "correction_source_links",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("correction_source_links")
    op.drop_table("answer_corrections")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_document_kind")
        batch_op.drop_column("contributor_name")
        batch_op.drop_column("document_kind")
