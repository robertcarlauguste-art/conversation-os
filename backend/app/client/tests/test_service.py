import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.repository import ClientRepository
from app.client.service import ClientService
from app.memory.models import PersonType

pytestmark = pytest.mark.usefixtures("_clean_client_tables")


async def test_find_or_create_creates_new_client_when_no_match(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    conversation_id = uuid.uuid4()

    client, was_created = await service.find_or_create(
        name="Jane Smith",
        role="buyer",
        entity_type=PersonType.CLIENT,
        conversation_id=conversation_id,
    )

    assert was_created is True
    assert client.full_name == "Jane Smith"
    assert client.role == "buyer"


async def test_find_or_create_matches_same_name_and_role(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    conv_a, conv_b = uuid.uuid4(), uuid.uuid4()

    first_client, first_created = await service.find_or_create(
        name="Jane Smith", role="buyer", entity_type=PersonType.CLIENT, conversation_id=conv_a
    )
    second_client, second_created = await service.find_or_create(
        name="jane smith",
        role="Buyer",
        entity_type=PersonType.CLIENT,
        conversation_id=conv_b,  # different case, must still match
    )

    assert first_created is True
    assert second_created is False
    assert second_client.id == first_client.id


async def test_find_or_create_does_not_match_same_name_different_role(
    db_session: AsyncSession,
) -> None:
    """FD-003: never auto-merge on name alone."""
    service = ClientService(ClientRepository(db_session))
    conv_a, conv_b = uuid.uuid4(), uuid.uuid4()

    buyer_client, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", entity_type=PersonType.CLIENT, conversation_id=conv_a
    )
    seller_client, seller_created = await service.find_or_create(
        name="Jane Smith", role="seller", entity_type=PersonType.CLIENT, conversation_id=conv_b
    )

    assert seller_created is True
    assert seller_client.id != buyer_client.id


async def test_find_or_create_does_not_auto_match_without_role(db_session: AsyncSession) -> None:
    """
    FD-003: no corroborating attribute (role missing) means no
    automatic match is even attempted — always creates a new client
    rather than guessing off name alone.
    """
    service = ClientService(ClientRepository(db_session))
    conv_a, conv_b = uuid.uuid4(), uuid.uuid4()

    first_client, _ = await service.find_or_create(
        name="Jane Smith", role=None, entity_type=PersonType.CLIENT, conversation_id=conv_a
    )
    second_client, second_created = await service.find_or_create(
        name="Jane Smith", role=None, entity_type=PersonType.CLIENT, conversation_id=conv_b
    )

    assert second_created is True
    assert second_client.id != first_client.id


async def test_record_facts_persists_with_full_provenance(db_session: AsyncSession) -> None:
    from app.conversation.enums import ConversationSource, ConversationStatus
    from app.conversation.models import Conversation
    from app.memory.models import Memory

    conversation = Conversation(
        filename="test.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=1024,
        status=ConversationStatus.COMPLETED,
        source=ConversationSource.UPLOAD,
    )
    db_session.add(conversation)
    await db_session.commit()

    memory = Memory(
        conversation_id=conversation.id,
        summary="A summary.",
        topics=["financing"],
        confidence=0.85,
        source="fake-model",
    )
    db_session.add(memory)
    await db_session.commit()

    service = ClientService(ClientRepository(db_session))
    client, _ = await service.find_or_create(
        name="Jane Smith",
        role="buyer",
        entity_type=PersonType.CLIENT,
        conversation_id=conversation.id,
    )

    facts = await service.record_facts(
        client_id=client.id,
        fact_texts=["financing", "timeline"],
        source_conversation_id=conversation.id,
        source_memory_id=memory.id,
        confidence=memory.confidence,
    )

    assert len(facts) == 2
    for fact in facts:
        assert fact.source_conversation_id == conversation.id
        assert fact.source_memory_id == memory.id
        assert fact.created_at is not None
        assert fact.confidence == 0.85


async def test_record_facts_rejects_blank_fact_text(db_session: AsyncSession) -> None:
    from app.client.validators import ClientValidationError

    service = ClientService(ClientRepository(db_session))
    client, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", entity_type=PersonType.CLIENT, conversation_id=uuid.uuid4()
    )

    try:
        await service.record_facts(
            client_id=client.id,
            fact_texts=["   "],
            source_conversation_id=uuid.uuid4(),
            source_memory_id=uuid.uuid4(),
            confidence=None,
        )
        raised = False
    except ClientValidationError:
        raised = True

    assert raised
