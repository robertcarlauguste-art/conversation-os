"""
Conversation service — the only layer allowed to make decisions about
what an upload means (Rule 3). Routes call this; this calls the
repository and storage backend.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.events import emit_conversation_uploaded
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository
from app.conversation.schemas import ConversationDetail
from app.conversation.storage import StorageBackend
from app.conversation.validators import UploadCandidate, ValidationError, validate_upload
from app.processing.visibility import safe_error
from app.services.base import BaseService

logger = logging.getLogger("conversation_os.conversation")


class ConversationNotFoundError(Exception):
    pass


class ConversationRetryConflict(Exception):
    pass


class ConversationRetryUnavailable(Exception):
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
        logger.info("upload_started size=%d", len(content))

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
                owner_id=self.repository.owner_id,
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
                "upload_completed conversation_id=%s duration_ms=%.2f status=%s",
                conversation.id,
                duration_ms,
                conversation.status.value,
            )
            return conversation

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "upload_failed duration_ms=%.2f error=%s",
                duration_ms,
                safe_error(str(exc)),
            )
            if isinstance(exc, ValidationError):
                raise
            raise RuntimeError("Upload failed. Check storage and database availability.") from None

    async def list_conversations(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
    ) -> list[Conversation]:
        return await self.repository.list_all(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        conversation = await self.repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        return conversation

    async def get_conversation_detail(self, conversation_id: uuid.UUID) -> ConversationDetail:
        conversation = await self.get_conversation(conversation_id)
        detail = ConversationDetail.model_validate(conversation)
        if detail.status == ConversationStatus.FAILED and not detail.processing_error:
            detail.processing_error = safe_error(
                await self.repository.latest_transcript_error(conversation_id)
            )
        return detail

    async def retry_conversation(
        self,
        conversation_id: uuid.UUID,
        enqueue: Callable[[uuid.UUID, int], Awaitable[None]],
    ) -> Conversation:
        try:
            conversation = await self.repository.get_for_retry(conversation_id)
            if conversation is None:
                raise ConversationNotFoundError("Conversation not found.")
            if conversation.status != ConversationStatus.FAILED:
                raise ConversationRetryConflict("Only failed conversations can be retried.")
            conversation.status = ConversationStatus.QUEUED
            conversation.processing_error = None
            conversation.processing_completed_at = None
            await self.repository.flush_retry(conversation)
            async with asyncio.timeout(10):
                await enqueue(conversation.id, conversation.processing_attempts)
            await self.repository.commit()
        except (ConversationNotFoundError, ConversationRetryConflict):
            await self._rollback_retry()
            raise
        except Exception:
            await self._rollback_retry()
            raise ConversationRetryUnavailable("Retry could not be queued.") from None
        logger.info(
            "conversation_retry_queued conversation_id=%s processing_attempts=%d",
            conversation.id,
            conversation.processing_attempts,
        )
        return conversation

    async def _rollback_retry(self) -> None:
        try:
            await self.repository.rollback()
        except Exception:
            raise ConversationRetryUnavailable("Retry could not be queued.") from None

    async def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        conversation = await self.get_conversation(conversation_id)
        await self._storage.delete(conversation.storage_path)
        await self.repository.delete_by_id(conversation_id)

    async def update_status(
        self, conversation_id: uuid.UUID, status: ConversationStatus
    ) -> Conversation:
        """
        Used by app/orchestrator/conversation_processing.py to move a
        conversation through UPLOADED → PROCESSING → COMPLETED/FAILED
        as the Sprint 2 pipeline runs. Added this sprint — Sprint 1
        only ever set status once, at upload.
        """
        conversation = await self.get_conversation(conversation_id)
        conversation.status = status
        await self.repository.commit()
        return conversation

    async def start_processing_attempt(self, conversation_id: uuid.UUID) -> Conversation:
        conversation = await self.get_conversation(conversation_id)
        conversation.processing_attempts += 1
        conversation.processing_error = None
        conversation.processing_started_at = datetime.now(UTC)
        conversation.processing_completed_at = None
        conversation.status = ConversationStatus.PROCESSING
        await self.repository.commit()
        return conversation

    async def finish_processing(
        self,
        conversation_id: uuid.UUID,
        *,
        status: ConversationStatus,
        error: str | None = None,
    ) -> Conversation:
        conversation = await self.get_conversation(conversation_id)
        conversation.status = status
        conversation.processing_error = safe_error(error)
        conversation.processing_completed_at = (
            datetime.now(UTC)
            if status in (ConversationStatus.FAILED, ConversationStatus.COMPLETED)
            else None
        )
        await self.repository.commit()
        return conversation

    async def update_client(
        self, conversation_id: uuid.UUID, client_id: uuid.UUID | None
    ) -> Conversation:
        """
        Sprint 3: sets which client this conversation is primarily
        about. Called automatically by the orchestrator's
        reconciliation stage, and manually via client/api.py's
        link/unlink endpoints (US-105) — `client_id=None` unlinks.
        """
        conversation = await self.get_conversation(conversation_id)
        conversation.client_id = client_id
        await self.repository.commit()
        return conversation
