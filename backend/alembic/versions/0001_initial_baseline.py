"""initial baseline - pgvector extension only, no application tables

Revision ID: 0001
Revises:
Create Date: 2026-07-07

Sprint 0 scope: enable the pgvector extension so future sprints can
add vector columns without a second migration for the extension
itself. No application tables are created here by design.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
