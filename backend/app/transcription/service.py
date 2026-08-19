"""
Transcription service.

Reads audio bytes from wherever the conversation slice's
`StorageBackend` put them, calls the injected `TranscriptionProvider`,
and persists the result. This service doesn't know or care which
storage backend or which STT vendor is behind those interfaces.
"""

import logging
import time
import uuid

from app.conversation.storage import StorageBackend
from app.providers.transcription_provider import (
    TranscriptionProvider,
)
from app.services.base import BaseService
from app.transcription.enums import TranscriptionStatus
from app.transcription.events import (
    emit_transcription_completed,
    emit_transcription_failed,
)
from app.transcription.models import Transcript
from app.transcription.repository import TranscriptRepository

logger = logging.getLogger("conversation_os.transcription")


class TranscriptionService(BaseService[TranscriptRepository]):
    def __init__(
        self,
        repository: TranscriptRepository,
        provider: TranscriptionProvider,
        storage: StorageBackend,
    ) -> None:
        super().__init__(repository)
        self._provider = provider
        self._storage = storage

    async def transcribe(
        self,
        *,
        conversation_id: uuid.UUID,
        storage_path: str,
        filename: str,
    ) -> Transcript:
        start = time.perf_counter()

        logger.info(
            "transcription_started conversation_id=%s",
            conversation_id,
        )

        transcript = Transcript(
            conversation_id=conversation_id,
            status=TranscriptionStatus.PROCESSING,
        )

        await self.repository.add(transcript)
        await self.repository.commit()

        try:
            # Read uploaded audio
            audio_bytes = await self._storage.read(storage_path)

            logger.info(
                "audio_read conversation_id=%s filename=%s bytes=%d",
                conversation_id,
                filename,
                len(audio_bytes),
            )

            # Send to Whisper
            result = await self._provider.transcribe(
                audio_bytes=audio_bytes,
                filename=filename,
            )

            logger.info(
                "whisper_result conversation_id=%s text_length=%d text=%r",
                conversation_id,
                len(result.text),
                result.text[:100],
            )

            # Persist transcript
            transcript.text = result.text
            transcript.language = result.language
            transcript.status = TranscriptionStatus.COMPLETED

            await self.repository.commit()

            emit_transcription_completed(
                conversation_id,
                transcript.id,
            )

            duration_ms = (time.perf_counter() - start) * 1000

            logger.info(
                "transcription_completed conversation_id=%s transcript_id=%s duration_ms=%.2f",
                conversation_id,
                transcript.id,
                duration_ms,
            )

            return transcript

        except Exception as exc:
            transcript.status = TranscriptionStatus.FAILED
            transcript.error_message = str(exc)

            await self.repository.commit()

            emit_transcription_failed(
                conversation_id,
                str(exc),
            )

            duration_ms = (time.perf_counter() - start) * 1000

            logger.warning(
                "transcription_failed conversation_id=%s duration_ms=%.2f error=%s",
                conversation_id,
                duration_ms,
                str(exc),
            )

            raise
