import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.models import Client, ClientFact
from app.client.repository import ClientRepository
from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.memory.models import Memory

pytestmark = pytest.mark.usefixtures("_clean_client_tables")


async def _make_conversation_and_memory(session: AsyncSession) -> tuple[Conversation, Memory]:
    conversation = Conversation(
        filename="test.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=1024,
        status=ConversationStatus.COMPLETED,
        source=ConversationSource.UPLOAD,
    )
    session.add(conversation)
    await session.commit()

    memory = Memory(
        conversation_id=conversation.id,
        summary="A summary.",
        topics=["financing"],
        confidence=0.9,
        source="fake-model",
    )
    session.add(memory)
    await session.commit()
    return conversation, memory


async def test_add_and_get_client(db_session: AsyncSession) -> None:
    repo = ClientRepository(db_session)
    client = Client(full_name="Jane Smith", role="buyer")
    await repo.add(client)
    await repo.commit()

    fetched = await repo.get(client.id)
    assert fetched is not None
    assert fetched.full_name == "Jane Smith"
    assert fetched.role == "buyer"


async def test_find_corroborated_match_requires_name_and_role(db_session: AsyncSession) -> None:
    repo = ClientRepository(db_session)
    client = Client(full_name="Jane Smith", role="buyer")
    await repo.add(client)
    await repo.commit()

    # Exact name + exact role -> match
    match = await repo.find_corroborated_match("jane smith", "buyer")
    assert match is not None
    assert match.id == client.id

    # Same name, different role -> no match (FD-003)
    no_match = await repo.find_corroborated_match("jane smith", "seller")
    assert no_match is None

    # Different name entirely -> no match
    no_match_2 = await repo.find_corroborated_match("john doe", "buyer")
    assert no_match_2 is None


async def test_list_all_sorted_by_updated_at(db_session: AsyncSession) -> None:
    repo = ClientRepository(db_session)
    first = Client(full_name="First Client", role="buyer")
    await repo.add(first)
    await repo.commit()

    second = Client(full_name="Second Client", role="buyer")
    await repo.add(second)
    await repo.commit()

    clients = await repo.list_all()
    names = [c.full_name for c in clients]
    assert names.index("Second Client") < names.index("First Client")


async def test_client_facts_persist_with_provenance(db_session: AsyncSession) -> None:
    conversation, memory = await _make_conversation_and_memory(db_session)
    repo = ClientRepository(db_session)

    client = Client(full_name="Jane Smith", role="buyer")
    await repo.add(client)
    await repo.commit()

    fact = ClientFact(
        client_id=client.id,
        fact_text="Prefers 3-bedroom homes",
        source_conversation_id=conversation.id,
        source_memory_id=memory.id,
        confidence=0.9,
    )
    repo.session.add(fact)
    await repo.commit()

    fetched = await repo.get_with_facts(client.id)
    assert fetched is not None
    assert len(fetched.facts) == 1
    assert fetched.facts[0].source_conversation_id == conversation.id
    assert fetched.facts[0].source_memory_id == memory.id
    assert fetched.facts[0].created_at is not None


async def test_get_returns_none_when_missing(db_session: AsyncSession) -> None:
    repo = ClientRepository(db_session)
    result = await repo.get(uuid.uuid4())
    assert result is None
