import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.models import Client
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession, owner_id: str = "dev_user") -> None:
        super().__init__(session, Client)
        self.owner_id = owner_id

    async def get(self, id_: object) -> Client | None:
        result = await self.session.execute(
            select(Client).where(Client.id == id_, Client.owner_id == self.owner_id)
        )
        return result.scalar_one_or_none()

    async def find_corroborated_match(
        self,
        normalized_name: str,
        normalized_role: str,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client).where(
                func.lower(Client.full_name) == normalized_name,
                func.lower(Client.role) == normalized_role,
                Client.owner_id == self.owner_id,
            )
        )

        return result.scalars().first()

    async def get_with_facts(
        self,
        client_id: uuid.UUID,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client)
            .options(
                selectinload(Client.facts),
                selectinload(Client.people),
                selectinload(Client.conversations),
            )
            .where(Client.id == client_id, Client.owner_id == self.owner_id)
            .execution_options(populate_existing=True)
        )

        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
        role: str | None = None,
    ) -> list[Client]:
        query = (
            select(Client)
            .options(
                selectinload(Client.facts),
                selectinload(Client.people),
                selectinload(Client.conversations),
            )
            .where(Client.owner_id == self.owner_id)
            .order_by(Client.updated_at.desc())
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                Client.full_name.ilike(term) | Client.email.ilike(term) | Client.phone.ilike(term)
            )
        if role:
            query = query.where(Client.role == role.strip().lower())
        query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)

        return list(result.scalars().all())
