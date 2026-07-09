import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository


def _make_conversation(**overrides) -> Conversation:
    defaults = dict(
        title="Buyer consultation",
        filename="buyer_consultation.mp3",
        storage_path="/tmp/fake.mp3",
        mime_type="audio/mpeg",
        file_size=2048,
        status=ConversationStatus.UPLOADED,
        source=ConversationSource.UPLOAD,
    )
    defaults.update(overrides)
    return Conversation(**defaults)


async def test_add_and_get(db_session: AsyncSession) -> None:
    repo = ConversationRepository(db_session)
    conversation = _make_conversation()

    await repo.add(conversation)
    await repo.commit()

    fetched = await repo.get(conversation.id)
    assert fetched is not None
    assert fetched.filename == "buyer_consultation.mp3"
    assert fetched.status == ConversationStatus.UPLOADED

    await repo.delete_by_id(conversation.id)


async def test_list_all_sorted_newest_first(db_session: AsyncSession) -> None:
    repo = ConversationRepository(db_session)
    first = _make_conversation(filename="first.mp3")
    second = _make_conversation(filename="second.mp3")

    await repo.add(first)
    await repo.commit()
    await repo.add(second)
    await repo.commit()

    conversations = await repo.list_all()
    filenames = [c.filename for c in conversations]
    assert filenames.index("second.mp3") < filenames.index("first.mp3")

    await repo.delete_by_id(first.id)
    await repo.delete_by_id(second.id)


async def test_get_missing_returns_none(db_session: AsyncSession) -> None:
    repo = ConversationRepository(db_session)
    result = await repo.get(uuid.uuid4())
    assert result is None


async def test_delete_by_id_removes_row(db_session: AsyncSession) -> None:
    repo = ConversationRepository(db_session)
    conversation = _make_conversation()
    await repo.add(conversation)
    await repo.commit()

    await repo.delete_by_id(conversation.id)

    assert await repo.get(conversation.id) is None
