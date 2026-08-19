"""expand memory entities

Revision ID: 31c729384386
Revises: 0004
Create Date: 2026-08-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "31c729384386"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# Upgrade
# ============================================================

def upgrade() -> None:

    # --------------------------------------------------------
    # ACTION ITEMS
    # --------------------------------------------------------

    # Preserve existing action item data
    op.alter_column(
        "action_items",
        "description",
        new_column_name="task",
        existing_type=sa.Text(),
        nullable=False,
    )


    # Add optional deadline field
    op.add_column(
        "action_items",
        sa.Column(
            "due",
            sa.String(length=255),
            nullable=True,
        )
    )


    # Create action status enum
    action_status = sa.Enum(
        "OPEN",
        "COMPLETED",
        "CANCELLED",
        name="action_status",
    )

    action_status.create(
        op.get_bind(),
        checkfirst=True,
    )


    # Add lifecycle state
    op.add_column(
        "action_items",
        sa.Column(
            "status",
            action_status,
            nullable=False,
            server_default="OPEN",
        )
    )


    # Remove default after existing rows are populated
    op.alter_column(
        "action_items",
        "status",
        server_default=None,
    )


    # --------------------------------------------------------
    # PEOPLE
    # --------------------------------------------------------

    person_type = sa.Enum(
        "CLIENT",
        "CONTACT",
        "AGENT",
        "VENDOR",
        "EMPLOYEE",
        "UNKNOWN",
        name="person_type",
    )

    person_type.create(
        op.get_bind(),
        checkfirst=True,
    )


    op.add_column(
        "people",
        sa.Column(
            "entity_type",
            person_type,
            nullable=False,
            server_default="UNKNOWN",
        )
    )


    op.alter_column(
        "people",
        "entity_type",
        server_default=None,
    )


    # --------------------------------------------------------
    # INDEXES
    # --------------------------------------------------------
    #
    # Keep existing indexes.
    # They are valuable for future memory search,
    # client reconciliation, and workflow queries.
    #
    # No index removals.
    #


# ============================================================
# Downgrade
# ============================================================

def downgrade() -> None:

    # Remove people entity classification
    op.drop_column(
        "people",
        "entity_type",
    )

    sa.Enum(
        name="person_type"
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )


    # Remove action item lifecycle fields
    op.drop_column(
        "action_items",
        "status",
    )

    op.drop_column(
        "action_items",
        "due",
    )


    # Restore original action item name
    op.alter_column(
        "action_items",
        "task",
        new_column_name="description",
        existing_type=sa.Text(),
        nullable=False,
    )


    sa.Enum(
        name="action_status"
    ).drop(
        op.get_bind(),
        checkfirst=True,
    )