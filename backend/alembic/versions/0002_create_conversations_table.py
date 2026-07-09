"""create conversations table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

conversation_status = postgresql.ENUM(
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="conversation_status",
)
conversation_source = postgresql.ENUM(
    "UPLOAD",
    "PHONE",
    "EMAIL",
    "IMPORT",
    name="conversation_source",
)

# Columns reference the same enum objects but with create_type=False,
# since the types are created explicitly (and idempotently) below —
# otherwise create_table's own DDL compiler tries to CREATE TYPE again.
conversation_status_column_type = postgresql.ENUM(
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="conversation_status",
    create_type=False,
)
conversation_source_column_type = postgresql.ENUM(
    "UPLOAD",
    "PHONE",
    "EMAIL",
    "IMPORT",
    name="conversation_source",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    conversation_status.create(bind, checkfirst=True)
    conversation_source.create(bind, checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", conversation_status_column_type, nullable=False),
        sa.Column("source", conversation_source_column_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_conversations_created_at", "conversations", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_table("conversations")
    conversation_source.drop(op.get_bind(), checkfirst=True)
    conversation_status.drop(op.get_bind(), checkfirst=True)
