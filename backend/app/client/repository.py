import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client.models import Client
from app.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Client)

    async def find_corroborated_match(
        self,
        normalized_name: str,
        normalized_role: str,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client).where(
                func.lower(Client.full_name) == normalized_name,
                func.lower(Client.role) == normalized_role,
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
            .where(Client.id == client_id)
            .execution_options(populate_existing=True)
        )

        return result.scalar_one_or_none()

    async def list_all(
        self,
    ) -> list[Client]:
        result = await self.session.execute(
            select(Client)
            .options(
                selectinload(Client.facts),
                selectinload(Client.people),
                selectinload(Client.conversations),
            )
            .order_by(Client.updated_at.desc())
        )

        return list(result.scalars().all())