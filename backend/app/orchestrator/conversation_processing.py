"""
Conversation processing orchestrator.

The first concrete `BaseOrchestrator` subclass — exactly the case
ADR-002 anticipated ("where a workflow genuinely spans multiple
domains, it goes through an orchestrator rather than one domain's
service reaching directly into another's").

Drives the full pipeline, Sprint 2 + Sprint 3:

    ConversationUploaded
        -> ConversationProcessingStarted
        -> [transcription]
        -> TranscriptionCompleted | TranscriptionFailed
        -> [memory extraction]
        -> MemoryCreated | skipped if transcript empty
        -> [client reconciliation]
        -> ClientCreated | ClientMatched | ClientProfileUpdated
        -> ConversationProcessed

This orchestrator currently runs synchronously inside the upload
request rather than as a background worker.
"""

import logging
import uuid

from app.client.service import ClientService
from app.conversation.enums import ConversationStatus
from app.conversation.events import (
    emit_conversation_processed,
    emit_conversation_processing_started,
)
from app.conversation.service import ConversationService
from app.memory.models import (
    Memory,
    PersonType,
)
from app.memory.service import MemoryService
from app.orchestrator.base import BaseOrchestrator
from app.processing.visibility import safe_error
from app.transcription.service import TranscriptionService

logger = logging.getLogger("conversation_os.orchestrator")


class ConversationProcessingOrchestrator(BaseOrchestrator):

    def __init__(
        self,
        conversation_service: ConversationService,
        transcription_service: TranscriptionService,
        memory_service: MemoryService,
        client_service: ClientService,
    ) -> None:

        self._conversations = conversation_service
        self._transcription = transcription_service
        self._memory = memory_service
        self._clients = client_service

    async def run(
        self,
        conversation_id: uuid.UUID,
    ) -> Memory | None:

        conversation = await self._conversations.get_conversation(conversation_id)

        await self._conversations.start_processing_attempt(conversation_id)

        emit_conversation_processing_started(conversation_id)

        error_message = (
            "Transcription failed. Check recording format and transcription provider configuration."
        )
        try:

            transcript = await self._transcription.transcribe(
                conversation_id=conversation_id,
                storage_path=conversation.storage_path,
                filename=conversation.filename,
            )

            error_message = "Memory extraction failed. Check the extraction provider configuration."
            memory = await self._memory.extract_and_persist(
                conversation_id=conversation_id,
                transcript_text=transcript.text or "",
            )

            if memory is not None:

                error_message = "Client reconciliation failed. Check database availability."
                await self._reconcile_people_to_clients(
                    conversation_id,
                    memory,
                )

                logger.info(
                    "conversation_processing_completed " "conversation_id=%s memory_id=%s",
                    conversation_id,
                    memory.id,
                )

            else:

                logger.info(
                    "conversation_processing_completed_without_memory " "conversation_id=%s",
                    conversation_id,
                )

            error_message = "Processing result could not be saved. Check database availability."
            await self._conversations.finish_processing(
                conversation_id,
                status=ConversationStatus.COMPLETED,
            )

            emit_conversation_processed(conversation_id)

            return memory

        except Exception:

            await self._conversations.finish_processing(
                conversation_id,
                status=ConversationStatus.FAILED,
                error=error_message,
            )

            logger.warning(
                "conversation_processing_failed conversation_id=%s",
                conversation_id,
            )

            raise RuntimeError(error_message) from None

    async def mark_failed(self, conversation_id: uuid.UUID, error: str) -> None:
        """Persist terminal worker failure after its failed transaction is rolled back."""
        await self._conversations.finish_processing(
            conversation_id,
            status=ConversationStatus.FAILED,
            error=safe_error(error),
        )

    async def _reconcile_people_to_clients(
        self,
        conversation_id: uuid.UUID,
        memory: Memory,
    ) -> None:
        """
        Sprint 3 client matching + provenance.

        Only extracted people classified as CLIENT
        become CRM clients.

        Other entities:

            AGENT
            CONTACT
            VENDOR
            EMPLOYEE
            UNKNOWN

        remain people records only.
        """

        matched_client_ids: set[uuid.UUID] = set()

        primary_client_id: uuid.UUID | None = None

        for person in memory.people:

            if person.entity_type != PersonType.CLIENT:

                logger.info(
                    "person_skipped_client_reconciliation " "person_id=%s entity_type=%s",
                    person.id,
                    person.entity_type.value,
                )

                continue

            client, _was_created = await self._clients.find_or_create(
                name=person.name,
                role=person.role,
                entity_type=person.entity_type,
                conversation_id=conversation_id,
            )

            await self._memory.link_person_to_client(
                person.id,
                client.id,
            )

            matched_client_ids.add(client.id)

            if primary_client_id is None:

                primary_client_id = client.id

        for client_id in matched_client_ids:

            await self._clients.record_facts(
                client_id=client_id,
                fact_texts=memory.topics,
                source_conversation_id=conversation_id,
                source_memory_id=memory.id,
                confidence=memory.confidence,
            )

        if primary_client_id is not None:

            await self._conversations.update_client(
                conversation_id,
                primary_client_id,
            )
