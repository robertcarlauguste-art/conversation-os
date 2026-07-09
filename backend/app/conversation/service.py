"""
Conversation service — the only layer allowed to make decisions about
what an upload means (Rule 3). Routes call this; this calls the
repository and storage backend.
"""

import logging
import time
import uuid

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.events import emit_conversation_uploaded
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository
from app.conversation.storage import StorageBackend
from app.conversation.validators import UploadCandidate, validate_upload
from app.services.base import BaseService

logger = logging.getLogger("conversation_os.conversation")


class ConversationNotFoundError(Exception):
    pass


class ConversationService(BaseService[ConversationRepository]):
    def __init__(
        self,
        repository: ConversationRepository,
        storage: StorageBackend,
        *,
        allowed_mime_types: tuple[str, ...],
        max_upload_size_bytes: int,
    ) -> None:
        super().__init__(repository)
        self._storage = storage
        self._allowed_mime_types = allowed_mime_types
        self._max_upload_size_bytes = max_upload_size_bytes

    async def upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
        title: str | None = None,
    ) -> Conversation:
        start = time.perf_counter()
        logger.info("upload_started filename=%s size=%d", filename, len(content))

        try:
            validate_upload(
                UploadCandidate(
                    filename=filename, content_type=content_type, size_bytes=len(content)
                ),
                allowed_mime_types=self._allowed_mime_types,
                max_size_bytes=self._max_upload_size_bytes,
            )

            storage_path = await self._storage.save(filename=filename, content=content)

            conversation = Conversation(
                title=title,
                filename=filename,
                storage_path=storage_path,
                mime_type=content_type or "application/octet-stream",
                file_size=len(content),
                status=ConversationStatus.UPLOADED,
                source=ConversationSource.UPLOAD,
            )
            await self.repository.add(conversation)
            await self.repository.commit()

            emit_conversation_uploaded(conversation.id, filename)

            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "upload_completed conversation_id=%s filename=%s duration_ms=%.2f status=%s",
                conversation.id,
                filename,
                duration_ms,
                conversation.status.value,
            )
            return conversation

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "upload_failed filename=%s duration_ms=%.2f error=%s",
                filename,
                duration_ms,
                str(exc),
            )
            raise

    async def list_conversations(self) -> list[Conversation]:
        return await self.repository.list_all()

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        conversation = await self.repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        return conversation

    async def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        conversation = await self.get_conversation(conversation_id)
        await self._storage.delete(conversation.storage_path)
        await self.repository.delete_by_id(conversation_id)
