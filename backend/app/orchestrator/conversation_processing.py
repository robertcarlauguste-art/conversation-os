"""
Conversation processing orchestrator.

The first concrete `BaseOrchestrator` subclass — exactly the case
ADR-002 anticipated ("where a workflow genuinely spans multiple
domains, it goes through an orchestrator rather than one domain's
service reaching directly into another's").

Drives the full pipeline, Sprint 2 + Sprint 3:

    ConversationUploaded (already emitted at upload time)
        -> ConversationProcessingStarted
        -> [transcription] -> TranscriptionCompleted | TranscriptionFailed
        -> [memory extraction] -> MemoryCreated, ActionItemsExtracted
        -> [client reconciliation] -> ClientCreated | ClientMatched,
                                       ClientProfileUpdated
                                       (own try/except — see run())
        -> ConversationProcessed | (status set to FAILED on any
                                     transcription/extraction error)

All events are logged synchronously in-process — no message broker,
no background worker process. This orchestrator itself currently runs
synchronously inside the upload request (see conversation/api.py)
rather than as a background task; that tradeoff is tracked as TD-003
in Sprint2.md, not hidden here.
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
from app.memory.models import Memory
from app.memory.service import MemoryService
from app.orchestrator.base import BaseOrchestrator
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

    async def run(self, conversation_id: uuid.UUID) -> Memory:
        conversation = await self._conversations.get_conversation(conversation_id)

        await self._conversations.update_status(conversation_id, ConversationStatus.PROCESSING)
        emit_conversation_processing_started(conversation_id)

        try:
            transcript = await self._transcription.transcribe(
                conversation_id=conversation_id,
                storage_path=conversation.storage_path,
                filename=conversation.filename,
            )

            memory = await self._memory.extract_and_persist(
                conversation_id=conversation_id,
                transcript_text=transcript.text or "",
            )

            # Reconciliation gets its own isolation: transcription and
            # extraction already succeeded by this point, and a
            # matching hiccup shouldn't erase that — the conversation
            # still completes; only the client-linking step is skipped
            # and logged.
            try:
                await self._reconcile_people_to_clients(conversation_id, memory)
            except Exception:
                logger.exception(
                    "client_reconciliation_failed conversation_id=%s memory_id=%s",
                    conversation_id,
                    memory.id,
                )

            await self._conversations.update_status(conversation_id, ConversationStatus.COMPLETED)
            emit_conversation_processed(conversation_id)
            return memory

        except Exception:
            await self._conversations.update_status(conversation_id, ConversationStatus.FAILED)
            logger.exception("conversation_processing_failed conversation_id=%s", conversation_id)
            raise

    async def _reconcile_people_to_clients(
        self, conversation_id: uuid.UUID, memory: Memory
    ) -> None:
        """
        FD-003 matching + FD-005 provenance, wired into the pipeline.

        Primary-client heuristic: the first extracted person whose
        role isn't "agent" is treated as the conversation's primary
        client (a real estate conversation typically involves a buyer
        or seller alongside an agent); falls back to the first person
        if no non-agent role is present. This is a simplification,
        not a claim of certainty — documented as a known limitation
        in Sprint3.md, not silently assumed.
        """
        matched_client_ids: set[uuid.UUID] = set()
        primary_client_id: uuid.UUID | None = None
        primary_is_non_agent = False

        for person in memory.people:
            client, _was_created = await self._clients.find_or_create(
                name=person.name, role=person.role, conversation_id=conversation_id
            )
            await self._memory.link_person_to_client(person.id, client.id)
            matched_client_ids.add(client.id)

            is_non_agent = (person.role or "").strip().lower() != "agent"
            if primary_client_id is None:
                primary_client_id = client.id
                primary_is_non_agent = is_non_agent
            elif is_non_agent and not primary_is_non_agent:
                # Upgrade from an agent (taken as a placeholder primary
                # since no better candidate had appeared yet) to the
                # first non-agent found — never downgrade once we have
                # a non-agent primary.
                primary_client_id = client.id
                primary_is_non_agent = True

        for client_id in matched_client_ids:
            await self._clients.record_facts(
                client_id=client_id,
                fact_texts=memory.topics,
                source_conversation_id=conversation_id,
                source_memory_id=memory.id,
                confidence=memory.confidence,
            )

        if primary_client_id is not None:
            await self._conversations.update_client(conversation_id, primary_client_id)
