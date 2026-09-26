"""Preserve the original extraction when users correct decisions and tasks."""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("decisions", "action_items"):
        op.add_column(table, sa.Column("original", sa.JSON(), nullable=True))


def downgrade() -> None:
    for table in ("action_items", "decisions"):
        op.drop_column(table, "original")
