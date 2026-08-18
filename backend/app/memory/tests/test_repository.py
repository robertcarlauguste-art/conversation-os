import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.memory.models import ActionItem, Decision, Memory, Person
from app.memory.repository import MemoryRepository


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


async def test_add_memory_with_children_and_get(db_session: AsyncSession) -> None:
    conversation = await _make_conversation(db_session)
    repo = MemoryRepository(db_session)

    memory = Memory(
        conversation_id=conversation.id,
        summary="A summary.",
        topics=["financing"],
        confidence=0.9,
        source="fake-model",
        decisions=[Decision(description="Decision A")],
        action_items=[ActionItem(task="Do the thing", due=None, owner=None)],
        people=[Person(name="Jane Doe", role=None)],
    )
    await repo.add(memory)
    await repo.commit()

    fetched = await repo.get(memory.id)
    assert fetched is not None
    assert fetched.summary == "A summary."
    assert len(fetched.decisions) == 1
    assert len(fetched.action_items) == 1
    assert len(fetched.people) == 1


async def test_get_by_conversation_id(db_session: AsyncSession) -> None:
    conversation = await _make_conversation(db_session)
    repo = MemoryRepository(db_session)

    memory = Memory(
        conversation_id=conversation.id,
        summary="Another summary.",
        topics=[],
        confidence=0.5,
        source="fake-model",
    )
    await repo.add(memory)
    await repo.commit()

    fetched = await repo.get_by_conversation_id(conversation.id)
    assert fetched is not None
    assert fetched.id == memory.id


async def test_get_by_conversation_id_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = MemoryRepository(db_session)
    result = await repo.get_by_conversation_id(uuid.uuid4())
    assert result is None


async def test_list_all_sorted_newest_first(db_session: AsyncSession) -> None:
    repo = MemoryRepository(db_session)

    conv_a = await _make_conversation(db_session)
    conv_b = await _make_conversation(db_session)

    memory_a = Memory(
        conversation_id=conv_a.id, summary="First", topics=[], confidence=0.5, source="fake"
    )
    await repo.add(memory_a)
    await repo.commit()

    memory_b = Memory(
        conversation_id=conv_b.id, summary="Second", topics=[], confidence=0.5, source="fake"
    )
    await repo.add(memory_b)
    await repo.commit()

    memories = await repo.list_all()
    summaries = [m.summary for m in memories]
    assert summaries.index("Second") < summaries.index("First")
