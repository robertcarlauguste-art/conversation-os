"""
Memory service.

Owns the:

Conversation → LLM → Structured JSON → Validation →
Persistence

pipeline's middle and end.
"""

import json
import logging
import time
import uuid


from app.memory.enums import MemoryType

from app.memory.events import (
    emit_action_items_extracted,
    emit_memory_created,
)

from app.memory.models import (
    ActionItem,
    ActionStatus,
    Decision,
    Memory,
    Person,
    PersonType,
)

from app.memory.repository import MemoryRepository

from app.memory.schemas import ExtractionResult

from app.memory.validators import (
    MemoryValidationError,
    validate_extraction,
)

from app.providers.ai_provider import (
    AIMessage,
    AIProvider,
)

from app.services.base import BaseService



logger = logging.getLogger(
    "conversation_os.memory"
)


class ActionItemNotFoundError(Exception):
    pass


class ActionItemService:
    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    async def complete(self, action_item_id: uuid.UUID) -> ActionItem:
        action_item = await self.repository.get_action_item(action_item_id)
        if action_item is None:
            raise ActionItemNotFoundError(
                f"Action item {action_item_id} not found."
            )
        if action_item.status != ActionStatus.COMPLETED:
            action_item = await self.repository.set_action_item_status(
                action_item,
                ActionStatus.COMPLETED,
            )
        return action_item



EXTRACTION_SYSTEM_PROMPT = """
You analyze a professional conversation transcript.

Extract structured memory information.

Return ONLY valid JSON.
Do not use markdown.
Do not use code blocks.
Do not add explanations.

The JSON must match this structure exactly:

{
  "summary": "2-4 sentence summary",

  "decisions": [
    "decision text"
  ],

  "action_items": [
    {
      "task": "what needs to be done",
      "due": "deadline if mentioned or null",
      "assignee": "person responsible if known or null"
    }
  ],

  "people": [
    {
      "name": "person name",
      "role": "professional role or relationship. Include company if useful.",
      "entity_type": "CLIENT | CONTACT | AGENT | VENDOR | EMPLOYEE | UNKNOWN"
    }
  ],

  "topics": [
    "topic label"
  ],

  "confidence": 0.0
}


ENTITY CLASSIFICATION RULES:

CLIENT:
- customer
- buyer
- seller
- person receiving a service
- person whose needs/goals are being managed

Examples:
John buying a home:
{
 "role": "Homebuyer",
 "entity_type": "CLIENT"
}


AGENT:
- realtor
- salesperson
- broker
- consultant
- representative
- service provider

Examples:
Sarah from ABC Realty:
{
 "role": "Realtor at ABC Realty",
 "entity_type": "AGENT"
}


CONTACT:
- someone mentioned but not receiving the service
- friend, referral, external contact


VENDOR:
- company or person providing goods/services


EMPLOYEE:
- internal employee of the organization


UNKNOWN:
- unclear relationship


Rules:

- Never invent people.
- Never invent deadlines.
- Never invent action items.
- If information is missing, use empty arrays.
- Confidence must be between 0 and 1.
- Prefer professional role over company name alone.
- Include company after role when available.
"""



class ExtractionError(Exception):
    """
    Raised when the LLM response cannot be parsed
    or validated.
    """



class MemoryService(
    BaseService[MemoryRepository]
):


    def __init__(
        self,
        repository: MemoryRepository,
        ai_provider: AIProvider,
        model: str,
    ) -> None:

        super().__init__(repository)

        self._ai_provider = ai_provider
        self._model = model



    async def extract_and_persist(
        self,
        *,
        conversation_id: uuid.UUID,
        transcript_text: str,
    ) -> Memory | None:


        start = time.perf_counter()


        logger.info(
            "extraction_started conversation_id=%s",
            conversation_id,
        )



        if not transcript_text or not transcript_text.strip():

            logger.info(
                "extraction_skipped_empty_transcript conversation_id=%s",
                conversation_id,
            )

            return None



        try:

            completion = await self._ai_provider.complete(
                messages=[
                    AIMessage(
                        role="user",
                        content=transcript_text,
                    )
                ],
                system=EXTRACTION_SYSTEM_PROMPT,
            )



            logger.info(
                "claude_raw_response conversation_id=%s response=%r",
                conversation_id,
                completion.content,
            )



            content = completion.content.strip()



            if content.startswith("```"):

                content = (
                    content
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )



            try:

                raw = json.loads(content)


            except json.JSONDecodeError as exc:

                raise ExtractionError(
                    f"LLM response was not valid JSON: {exc}. "
                    f"Raw response: {content[:500]}"
                ) from exc



            extraction = ExtractionResult.model_validate(
                raw
            )


            validate_extraction(
                extraction
            )



            logger.info(
                "memory_extracted conversation_id=%s decisions=%s action_items=%s people=%s topics=%s confidence=%.2f",
                conversation_id,
                len(extraction.decisions),
                len(extraction.action_items),
                len(extraction.people),
                len(extraction.topics),
                extraction.confidence,
            )



            for person in extraction.people:

                logger.info(
                    "entity_detected name=%s role=%s type=%s",
                    person.name,
                    person.role,
                    person.entity_type,
                )



            memory = await self._persist(
                conversation_id=conversation_id,
                extraction=extraction,
                source=completion.model,
            )



            emit_memory_created(
                conversation_id,
                memory.id,
            )



            emit_action_items_extracted(
                conversation_id,
                memory.id,
                len(memory.action_items),
            )



            duration_ms = (
                time.perf_counter() - start
            ) * 1000



            logger.info(
                "extraction_completed conversation_id=%s memory_id=%s duration_ms=%.2f",
                conversation_id,
                memory.id,
                duration_ms,
            )



            return memory




        except (
            ExtractionError,
            MemoryValidationError,
        ) as exc:


            duration_ms = (
                time.perf_counter() - start
            ) * 1000



            logger.warning(
                "extraction_failed conversation_id=%s duration_ms=%.2f error=%s",
                conversation_id,
                duration_ms,
                str(exc),
            )


            raise





    def _safe_person_type(
        self,
        value: PersonType | str | None,
    ) -> PersonType:


        if not value:

            return PersonType.UNKNOWN



        if isinstance(
            value,
            PersonType,
        ):

            return value



        try:

            return PersonType(
                value.upper()
            )


        except ValueError:

            return PersonType.UNKNOWN





    async def _persist(
        self,
        *,
        conversation_id: uuid.UUID,
        extraction: ExtractionResult,
        source: str,
    ) -> Memory:



        memory = Memory(

            conversation_id=conversation_id,

            summary=extraction.summary,

            memory_type=MemoryType.CONVERSATION_SUMMARY,

            topics=extraction.topics,

            confidence=extraction.confidence,

            source=source,


            decisions=[
                Decision(
                    description=d
                )
                for d in extraction.decisions
            ],


            action_items=[

                ActionItem(

                    task=item.task,

                    due=item.due,

                    owner=item.assignee,

                    status=ActionStatus.OPEN,

                )

                for item in extraction.action_items

            ],



            people=[

                Person(

                    name=person.name,

                    role=person.role,

                    entity_type=self._safe_person_type(
                        person.entity_type
                    ),

                )

                for person in extraction.people

            ],


        )



        await self.repository.add(
            memory
        )


        await self.repository.commit()



        return memory





    async def get_by_conversation_id(
        self,
        conversation_id: uuid.UUID,
    ) -> Memory | None:


        return await self.repository.get_by_conversation_id(
            conversation_id
        )





    async def list_memories(
        self,
    ) -> list[Memory]:


        return await self.repository.list_all()





    async def link_person_to_client(
        self,
        person_id: uuid.UUID,
        client_id: uuid.UUID,
    ) -> None:


        await self.repository.set_person_client(
            person_id,
            client_id,
        )
