"""Add hidden QA entries and provenance links."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260717_0003"
down_revision = "20260716_0002"
branch_labels = None
depends_on = None


answer_origin_enum = sa.Enum(
    "KNOWLEDGE_BASE",
    "WEB_SEARCH",
    "HYBRID",
    "NO_ANSWER",
    name="answerorigin",
)


def _add_hybrid_answer_origin() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    values = "ENUM('KNOWLEDGE_BASE','WEB_SEARCH','HYBRID','NO_ANSWER')"
    op.execute(f"ALTER TABLE messages MODIFY answer_origin {values} NULL")
    op.execute(f"ALTER TABLE answer_knowledge_tasks MODIFY source_answer_origin {values} NULL")


def upgrade() -> None:
    _add_hybrid_answer_origin()

    op.create_table(
        "qa_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("question_hash", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_answer_origin", answer_origin_enum, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qa_entries_created_by", "qa_entries", ["created_by"], unique=False)
    op.create_index("ix_qa_entries_content_hash", "qa_entries", ["content_hash"], unique=False)
    op.create_index("ix_qa_entries_is_active", "qa_entries", ["is_active"], unique=False)
    op.create_index("ix_qa_entries_question_hash", "qa_entries", ["question_hash"], unique=True)

    op.create_table(
        "qa_source_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("qa_entry_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("source_chunk_id", sa.BigInteger(), nullable=True),
        sa.Column("marker", sa.String(length=1), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["qa_entry_id"], ["qa_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qa_entry_id", "document_id"),
    )
    op.create_index(
        "ix_qa_source_links_document_id", "qa_source_links", ["document_id"], unique=False
    )
    op.create_index(
        "ix_qa_source_links_qa_entry_id", "qa_source_links", ["qa_entry_id"], unique=False
    )

    with op.batch_alter_table("answer_knowledge_tasks") as batch_op:
        batch_op.add_column(sa.Column("qa_entry_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_answer_knowledge_tasks_qa_entry_id", ["qa_entry_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_answer_knowledge_tasks_qa_entry_id",
            "qa_entries",
            ["qa_entry_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("answer_knowledge_tasks") as batch_op:
        batch_op.drop_constraint("fk_answer_knowledge_tasks_qa_entry_id", type_="foreignkey")
        batch_op.drop_index("ix_answer_knowledge_tasks_qa_entry_id")
        batch_op.drop_column("qa_entry_id")
    op.drop_table("qa_source_links")
    op.drop_table("qa_entries")

    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        values = "ENUM('KNOWLEDGE_BASE','WEB_SEARCH','NO_ANSWER')"
        op.execute(f"ALTER TABLE messages MODIFY answer_origin {values} NULL")
        op.execute(f"ALTER TABLE answer_knowledge_tasks MODIFY source_answer_origin {values} NULL")
