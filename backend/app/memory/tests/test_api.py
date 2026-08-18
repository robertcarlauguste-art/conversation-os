from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.main import app
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService
from tests.fakes import FakeAIProvider


async def _make_conversation_with_memory(session: AsyncSession) -> Conversation:
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

    service = MemoryService(MemoryRepository(session), FakeAIProvider(), model="fake-claude")
    await service.extract_and_persist(conversation_id=conversation.id, transcript_text="text")
    return conversation


async def test_get_memory_by_conversation(db_session: AsyncSession) -> None:
    conversation = await _make_conversation_with_memory(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/memories/by-conversation/{conversation.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["conversation_id"] == str(conversation.id)
    assert len(body["data"]["decisions"]) == 1
    assert len(body["data"]["action_items"]) == 2
    assert len(body["data"]["people"]) == 2


async def test_get_memory_by_conversation_404_when_missing() -> None:
    import uuid

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/memories/by-conversation/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_list_memories_includes_created(db_session: AsyncSession) -> None:
    conversation = await _make_conversation_with_memory(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/memories")

    assert response.status_code == 200
    conversation_ids = [item["conversation_id"] for item in response.json()["data"]]
    assert str(conversation.id) in conversation_ids


async def test_get_memory_by_id(db_session: AsyncSession) -> None:
    conversation = await _make_conversation_with_memory(db_session)
    repo = MemoryRepository(db_session)
    memory = await repo.get_by_conversation_id(conversation.id)
    assert memory is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/memories/{memory.id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(memory.id)


async def test_complete_action_item(db_session: AsyncSession) -> None:
    conversation = await _make_conversation_with_memory(db_session)
    repo = MemoryRepository(db_session)
    memory = await repo.get_by_conversation_id(conversation.id)
    assert memory is not None
    action_item = memory.action_items[0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/memories/action-items/{action_item.id}/complete"
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "COMPLETED"
    assert response.json()["data"]["completed_at"] is not None
    await db_session.refresh(action_item)
    assert action_item.status.value == "COMPLETED"
    assert action_item.completed_at is not None


async def test_complete_action_item_404_when_missing() -> None:
    import uuid

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/memories/action-items/{uuid.uuid4()}/complete"
        )

    assert response.status_code == 404
