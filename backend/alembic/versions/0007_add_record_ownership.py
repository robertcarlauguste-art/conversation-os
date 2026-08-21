"""add record ownership

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("clients", "conversations"):
        op.add_column(
            table,
            sa.Column("owner_id", sa.String(length=255), nullable=True),
        )
        op.execute(sa.text(f"UPDATE {table} SET owner_id = 'dev_user' WHERE owner_id IS NULL"))
        op.alter_column(table, "owner_id", nullable=False)
        op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])


def downgrade() -> None:
    for table in ("conversations", "clients"):
        op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_column(table, "owner_id")
