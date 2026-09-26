"""Persist source-checked client reviews."""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("saved_review", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "saved_review")
