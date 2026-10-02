"""Preserve an explicitly confirmed name separately from extracted text."""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("people", sa.Column("confirmed_name", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("people", "confirmed_name")
