"""
Shared declarative base.

Every domain's ORM models (e.g. `conversation/models.py`) subclass
`Base` from here, so Alembic's autogenerate can see all tables
through one `target_metadata` object, and so there's exactly one
answer to "what connects a model to the database" across slices.

This was flagged as a Sprint 0 risk (target_metadata was None because
no models existed yet) — resolved now that Sprint 1 has a real table.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
