import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.models import Client
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Client)

    async def find_corroborated_match(
        self, normalized_name: str, normalized_role: str
    ) -> Client | None:
        """
        FD-003's corroborating-attribute check: exact name AND exact
        role, both required — matching name alone never returns a
        result here. `role` is the last-reconciled role stored on
        `Client` (see models.py's docstring for why it isn't a live
        cross-slice query against `people`).
        """
        result = await self.session.execute(
            select(Client).where(
                func.lower(Client.full_name) == normalized_name,
                func.lower(Client.role) == normalized_role,
            )
        )
        return result.scalars().first()

    async def get_with_facts(self, client_id: uuid.UUID) -> Client | None:
        """
        Explicit query rather than `self.get()` (which uses
        `session.get()`): `session.get()` shortcuts to the identity
        map for an object already loaded earlier in the same session
        (e.g. just created via `find_or_create`), skipping the
        `facts` relationship's `selectin` eager-load in that case —
        this discovered itself as a real `MissingGreenlet` failure
        when a test created a client then re-fetched it in the same
        session. `populate_existing=True` forces the relationship to
        (re)load regardless of identity-map state.
        """
        result = await self.session.execute(
            select(Client).where(Client.id == client_id).execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Client]:
        result = await self.session.execute(select(Client).order_by(Client.updated_at.desc()))
        return list(result.scalars().all())
