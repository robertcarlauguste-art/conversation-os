import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.main import app
from app.transcription.enums import TranscriptionStatus
from app.transcription.models import Transcript


async def _make_conversation_with_transcript(session: AsyncSession) -> Conversation:
    conversation = Conversation(
        filename="test.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=1024,
        status=ConversationStatus.PROCESSING,
        source=ConversationSource.UPLOAD,
    )
    session.add(conversation)
    await session.commit()

    transcript = Transcript(
        conversation_id=conversation.id,
        text="hello world",
        language="en",
        status=TranscriptionStatus.COMPLETED,
    )
    session.add(transcript)
    await session.commit()
    return conversation


async def test_get_transcript_by_conversation(db_session: AsyncSession) -> None:
    conversation = await _make_conversation_with_transcript(db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/transcriptions/by-conversation/{conversation.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["text"] == "hello world"
    assert body["data"]["status"] == "COMPLETED"


async def test_get_transcript_by_conversation_404_when_missing() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/transcriptions/by-conversation/{uuid.uuid4()}")

    assert response.status_code == 404
