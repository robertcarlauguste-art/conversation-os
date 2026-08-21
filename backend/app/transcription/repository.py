import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.models import Conversation
from app.repositories.base import BaseRepository
from app.transcription.models import Transcript


class TranscriptRepository(BaseRepository[Transcript]):
    def __init__(self, session: AsyncSession, owner_id: str = "dev_user") -> None:
        super().__init__(session, Transcript)
        self.owner_id = owner_id

    async def get_by_conversation_id(self, conversation_id: uuid.UUID) -> Transcript | None:
        result = await self.session.execute(
            select(Transcript)
            .join(Conversation, Transcript.conversation_id == Conversation.id)
            .where(
                Transcript.conversation_id == conversation_id,
                Conversation.owner_id == self.owner_id,
            )
        )
        return result.scalar_one_or_none()
