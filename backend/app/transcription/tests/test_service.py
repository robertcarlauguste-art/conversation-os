from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.conversation.storage import LocalStorageBackend
from app.transcription.enums import TranscriptionStatus
from app.transcription.repository import TranscriptRepository
from app.transcription.service import TranscriptionService
from tests.fakes import FakeTranscriptionProvider


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


async def test_transcribe_persists_completed_transcript(
    db_session: AsyncSession, storage_backend: LocalStorageBackend
) -> None:
    conversation = await _make_conversation(db_session)
    storage_path = await storage_backend.save(filename="test.mp3", content=b"fake audio bytes")

    service = TranscriptionService(
        TranscriptRepository(db_session),
        FakeTranscriptionProvider(text="hello world"),
        storage_backend,
    )

    transcript = await service.transcribe(
        conversation_id=conversation.id, storage_path=storage_path, filename="test.mp3"
    )

    assert transcript.status == TranscriptionStatus.COMPLETED
    assert transcript.text == "hello world"
    assert transcript.language == "en"


async def test_transcribe_marks_failed_on_missing_file(
    db_session: AsyncSession, storage_backend: LocalStorageBackend
) -> None:
    conversation = await _make_conversation(db_session)
    service = TranscriptionService(
        TranscriptRepository(db_session), FakeTranscriptionProvider(), storage_backend
    )

    try:
        await service.transcribe(
            conversation_id=conversation.id,
            storage_path="/nonexistent/path.mp3",
            filename="test.mp3",
        )
        raised = False
    except FileNotFoundError:
        raised = True

    assert raised

    repo = TranscriptRepository(db_session)
    transcript = await repo.get_by_conversation_id(conversation.id)
    assert transcript is not None
    assert transcript.status == TranscriptionStatus.FAILED
    assert transcript.error_message is not None


async def test_get_by_conversation_id_returns_none_when_missing(db_session: AsyncSession) -> None:
    import uuid

    repo = TranscriptRepository(db_session)
    result = await repo.get_by_conversation_id(uuid.uuid4())
    assert result is None
