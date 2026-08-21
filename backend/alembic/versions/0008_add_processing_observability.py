"""add processing observability

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("conversations", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "processing_completed_at")
    op.drop_column("conversations", "processing_started_at")
    op.drop_column("conversations", "processing_error")
    op.drop_column("conversations", "processing_attempts")
