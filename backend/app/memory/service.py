"""
Memory service.

Owns the "Conversation → LLM → Structured JSON → Validation →
Persistence" pipeline's middle and end. Getting text from a
conversation into this service is the orchestrator's job (it calls
TranscriptionService first); this service only knows about a
transcript's text, not how it was produced.
"""

import json
import logging
import time
import uuid

from app.memory.enums import MemoryType
from app.memory.events import emit_action_items_extracted, emit_memory_created
from app.memory.models import ActionItem, Decision, Memory, Person
from app.memory.repository import MemoryRepository
from app.memory.schemas import ExtractionResult
from app.memory.validators import MemoryValidationError, validate_extraction
from app.providers.ai_provider import AIMessage, AIProvider
from app.services.base import BaseService

logger = logging.getLogger("conversation_os.memory")

EXTRACTION_SYSTEM_PROMPT = """\
You analyze a professional conversation transcript (e.g. a real \
estate consultation) and extract structured information from it.

Respond with ONLY a single JSON object, no other text, matching \
exactly this shape:

{
  "summary": "2-4 sentence summary of the conversation",
  "decisions": ["decision made during the conversation", ...],
  "action_items": ["concrete follow-up action", ...],
  "people": ["name of a person mentioned or present", ...],
  "topics": ["short topic label", ...],
  "confidence": 0.0 to 1.0, how confident you are in this extraction
}

If the transcript has no clear decisions, action items, people, or \
topics, return an empty list for that field rather than guessing.
"""


class ExtractionError(Exception):
    """Raised when the LLM's response can't be parsed/validated. Message is log-facing."""


class MemoryService(BaseService[MemoryRepository]):
    def __init__(self, repository: MemoryRepository, ai_provider: AIProvider, model: str) -> None:
        super().__init__(repository)
        self._ai_provider = ai_provider
        self._model = model

    async def extract_and_persist(
        self, *, conversation_id: uuid.UUID, transcript_text: str
    ) -> Memory:
        start = time.perf_counter()
        logger.info("extraction_started conversation_id=%s", conversation_id)

        try:
            completion = await self._ai_provider.complete(
                messages=[AIMessage(role="user", content=transcript_text)],
                system=EXTRACTION_SYSTEM_PROMPT,
            )

            try:
                raw = json.loads(completion.content)
            except json.JSONDecodeError as exc:
                raise ExtractionError(f"LLM response was not valid JSON: {exc}") from exc

            extraction = ExtractionResult.model_validate(raw)
            validate_extraction(extraction)

            memory = await self._persist(
                conversation_id=conversation_id,
                extraction=extraction,
                source=completion.model,
            )

            emit_memory_created(conversation_id, memory.id)
            emit_action_items_extracted(conversation_id, memory.id, len(memory.action_items))

            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "extraction_completed conversation_id=%s memory_id=%s duration_ms=%.2f",
                conversation_id,
                memory.id,
                duration_ms,
            )
            return memory

        except (ExtractionError, MemoryValidationError) as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "extraction_failed conversation_id=%s duration_ms=%.2f error=%s",
                conversation_id,
                duration_ms,
                str(exc),
            )
            raise

    async def _persist(
        self, *, conversation_id: uuid.UUID, extraction: ExtractionResult, source: str
    ) -> Memory:
        memory = Memory(
            conversation_id=conversation_id,
            summary=extraction.summary,
            memory_type=MemoryType.CONVERSATION_SUMMARY,
            topics=extraction.topics,
            confidence=extraction.confidence,
            source=source,
            decisions=[Decision(description=d) for d in extraction.decisions],
            action_items=[ActionItem(description=a) for a in extraction.action_items],
            people=[Person(name=p) for p in extraction.people],
        )
        await self.repository.add(memory)
        await self.repository.commit()
        return memory

    async def get_by_conversation_id(self, conversation_id: uuid.UUID) -> Memory | None:
        return await self.repository.get_by_conversation_id(conversation_id)

    async def list_memories(self) -> list[Memory]:
        return await self.repository.list_all()

    async def link_person_to_client(self, person_id: uuid.UUID, client_id: uuid.UUID) -> None:
        """Sprint 3 — called by the orchestrator's reconciliation stage."""
        await self.repository.set_person_client(person_id, client_id)
