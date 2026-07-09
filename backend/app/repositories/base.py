"""
Base repository (Rule 2: database access must occur through repositories).

Think of this like a librarian. Services never rummage through the
shelves (the database) themselves — they hand a request to the
librarian (the repository), and the librarian fetches or files things
in the right place. This keeps the "how data is stored" question in
one spot, so it can change later without every service noticing.

No concrete tables exist yet (Sprint 0 scope), so this is the
abstract librarian only — domain-specific repositories (e.g.
`app/conversation/repository.py` in Sprint 1) will subclass this and
live inside their own domain package, not here. This module holds
only the shared, domain-agnostic base class.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository[ModelType]:
    """Generic async repository base class. Subclass per domain model."""

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def get(self, id_: object) -> ModelType | None:
        return await self.session.get(self.model, id_)

    async def add(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def commit(self) -> None:
        await self.session.commit()
