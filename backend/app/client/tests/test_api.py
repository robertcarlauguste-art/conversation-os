import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.repository import ClientRepository
from app.client.service import ClientService
from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.main import app


async def _make_conversation(session: AsyncSession, **overrides) -> Conversation:
    defaults = dict(
        filename="test.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=1024,
        status=ConversationStatus.COMPLETED,
        source=ConversationSource.UPLOAD,
    )
    defaults.update(overrides)
    conversation = Conversation(**defaults)
    session.add(conversation)
    await session.commit()
    return conversation


async def test_list_clients_includes_created(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    client, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", conversation_id=uuid.uuid4()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/api/v1/clients")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert str(client.id) in ids


async def test_get_client_404_when_missing() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get(f"/api/v1/clients/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_client_returns_facts(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    conversation = await _make_conversation(db_session)

    from app.memory.models import Memory

    memory = Memory(
        conversation_id=conversation.id,
        summary="summary",
        topics=["financing"],
        confidence=0.8,
        source="fake-model",
    )
    db_session.add(memory)
    await db_session.commit()

    client, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", conversation_id=conversation.id
    )
    await service.record_facts(
        client_id=client.id,
        fact_texts=["financing"],
        source_conversation_id=conversation.id,
        source_memory_id=memory.id,
        confidence=0.8,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get(f"/api/v1/clients/{client.id}")

    assert response.status_code == 200
    body = response.json()["data"]
    assert len(body["facts"]) == 1
    assert body["facts"][0]["source_conversation_id"] == str(conversation.id)


async def test_link_and_unlink_conversation(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    client, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", conversation_id=uuid.uuid4()
    )
    conversation = await _make_conversation(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        link_response = await http.post(
            f"/api/v1/clients/{client.id}/conversations/{conversation.id}"
        )
        assert link_response.status_code == 204

        list_response = await http.get(f"/api/v1/clients/{client.id}/conversations")
        assert list_response.status_code == 200
        conversation_ids = [c["id"] for c in list_response.json()["data"]]
        assert str(conversation.id) in conversation_ids

        unlink_response = await http.delete(
            f"/api/v1/clients/{client.id}/conversations/{conversation.id}"
        )
        assert unlink_response.status_code == 204

        list_response_2 = await http.get(f"/api/v1/clients/{client.id}/conversations")
        conversation_ids_2 = [c["id"] for c in list_response_2.json()["data"]]
        assert str(conversation.id) not in conversation_ids_2


async def test_unlink_wrong_client_returns_404(db_session: AsyncSession) -> None:
    service = ClientService(ClientRepository(db_session))
    client_a, _ = await service.find_or_create(
        name="Jane Smith", role="buyer", conversation_id=uuid.uuid4()
    )
    client_b, _ = await service.find_or_create(
        name="John Doe", role="seller", conversation_id=uuid.uuid4()
    )
    conversation = await _make_conversation(db_session, client_id=client_a.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.delete(
            f"/api/v1/clients/{client_b.id}/conversations/{conversation.id}"
        )
        assert response.status_code == 404
