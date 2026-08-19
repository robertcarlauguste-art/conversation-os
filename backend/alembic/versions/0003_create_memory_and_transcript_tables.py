"""create transcripts, memories, decisions, action_items, people tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

transcription_status_type = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="transcription_status"
)
transcription_status_column = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="transcription_status", create_type=False
)

memory_type_type = postgresql.ENUM("CONVERSATION_SUMMARY", name="memory_type")
memory_type_column = postgresql.ENUM(
    "CONVERSATION_SUMMARY", name="memory_type", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    transcription_status_type.create(bind, checkfirst=True)
    memory_type_type.create(bind, checkfirst=True)

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("status", transcription_status_column, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("conversation_id", name="uq_transcripts_conversation_id"),
    )

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("memory_type", memory_type_column, nullable=False),
        sa.Column("topics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("conversation_id", name="uq_memories_conversation_id"),
    )

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "memory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "action_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "memory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "memory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_index("ix_decisions_memory_id", "decisions", ["memory_id"])
    op.create_index("ix_action_items_memory_id", "action_items", ["memory_id"])
    op.create_index("ix_people_memory_id", "people", ["memory_id"])


def downgrade() -> None:
    op.drop_index("ix_people_memory_id", table_name="people")
    op.drop_index("ix_action_items_memory_id", table_name="action_items")
    op.drop_index("ix_decisions_memory_id", table_name="decisions")
    op.drop_table("people")
    op.drop_table("action_items")
    op.drop_table("decisions")
    op.drop_table("memories")
    op.drop_table("transcripts")
    memory_type_type.drop(op.get_bind(), checkfirst=True)
    transcription_status_type.drop(op.get_bind(), checkfirst=True)
