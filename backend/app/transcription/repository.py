import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.transcription.models import Transcript


class TranscriptRepository(BaseRepository[Transcript]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Transcript)

    async def get_by_conversation_id(self, conversation_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript).where(Transcript.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()
