"""create client follow-up action history

Revision ID: 0005
Revises: 31c729384386
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005"
down_revision: Union[str, None] = "31c729384386"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    followup_action = postgresql.ENUM(
        "COMPLETE",
        "SNOOZE",
        "RECORD_CONTACT",
        name="followup_action",
        create_type=False,
    )
    followup_action.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "client_followup_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", followup_action, nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"], ["clients.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_client_followup_actions_client_id",
        "client_followup_actions",
        ["client_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_client_followup_actions_client_id",
        table_name="client_followup_actions",
    )
    op.drop_table("client_followup_actions")
    sa.Enum(name="followup_action").drop(op.get_bind(), checkfirst=True)
