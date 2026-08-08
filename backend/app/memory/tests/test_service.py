import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.memory.repository import MemoryRepository
from app.memory.service import ExtractionError, MemoryService
from app.memory.validators import MemoryValidationError
from tests.fakes import FakeAIProvider


async def _make_conversation(session: AsyncSession) -> Conversation:
    conversation = Conversation(
        filename="test.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=1024,
        status=ConversationStatus.UPLOADED,
        source=ConversationSource.UPLOAD,
    )
    session.add(conversation)
    await session.commit()
    return conversation


async def test_extract_and_persist_creates_memory_with_children(db_session: AsyncSession) -> None:
    conversation = await _make_conversation(db_session)
    service = MemoryService(MemoryRepository(db_session), FakeAIProvider(), model="fake-claude")

    memory = await service.extract_and_persist(
        conversation_id=conversation.id, transcript_text="some transcript text"
    )

    assert memory.summary
    assert len(memory.decisions) == 1
    assert len(memory.action_items) == 2
    assert len(memory.people) == 2
    assert memory.topics == ["financing", "offer terms", "timeline"]
    assert memory.source == "fake-claude"


async def test_extract_and_persist_raises_on_invalid_json(db_session: AsyncSession) -> None:
    conversation = await _make_conversation(db_session)
    service = MemoryService(
        MemoryRepository(db_session), FakeAIProvider(response_json="not valid json"), model="fake"
    )

    with pytest.raises(ExtractionError):
        await service.extract_and_persist(conversation_id=conversation.id, transcript_text="text")


async def test_extract_and_persist_raises_on_business_rule_violation(
    db_session: AsyncSession,
) -> None:
    conversation = await _make_conversation(db_session)
    bad_json = json.dumps(
        {
            "summary": "   ",
            "decisions": [],
            "action_items": [],
            "people": [],
            "topics": [],
            "confidence": 0.5,
        }
    )
    service = MemoryService(
        MemoryRepository(db_session), FakeAIProvider(response_json=bad_json), model="fake"
    )

    with pytest.raises(MemoryValidationError):
        await service.extract_and_persist(conversation_id=conversation.id, transcript_text="text")


async def test_get_by_conversation_id(db_session: AsyncSession) -> None:
    conversation = await _make_conversation(db_session)
    service = MemoryService(MemoryRepository(db_session), FakeAIProvider(), model="fake-claude")
    created = await service.extract_and_persist(
        conversation_id=conversation.id, transcript_text="text"
    )

    fetched = await service.get_by_conversation_id(conversation.id)
    assert fetched is not None
    assert fetched.id == created.id
