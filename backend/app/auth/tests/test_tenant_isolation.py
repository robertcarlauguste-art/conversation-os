from app.client.models import Client
from app.client.repository import ClientRepository
from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository


def conversation(owner_id: str, filename: str) -> Conversation:
    return Conversation(
        owner_id=owner_id,
        filename=filename,
        storage_path=f"/tmp/{filename}",
        mime_type="audio/mpeg",
        file_size=10,
        status=ConversationStatus.UPLOADED,
        source=ConversationSource.UPLOAD,
    )


async def test_conversation_repository_hides_other_owners(db_session) -> None:
    owner_a = ConversationRepository(db_session, "user_a")
    owner_b = ConversationRepository(db_session, "user_b")
    a_record = await owner_a.add(conversation("user_a", "a.mp3"))
    await owner_b.add(conversation("user_b", "b.mp3"))
    await owner_a.commit()

    assert [item.filename for item in await owner_a.list_all()] == ["a.mp3"]
    assert await owner_b.get(a_record.id) is None


async def test_client_matching_and_reads_are_owner_scoped(db_session) -> None:
    owner_a = ClientRepository(db_session, "user_a")
    owner_b = ClientRepository(db_session, "user_b")
    a_client = await owner_a.add(Client(owner_id="user_a", full_name="Jane", role="buyer"))
    await owner_b.add(Client(owner_id="user_b", full_name="Jane", role="buyer"))
    await owner_a.commit()

    match = await owner_a.find_corroborated_match("jane", "buyer")
    assert match is not None and match.owner_id == "user_a"
    assert await owner_b.get(a_client.id) is None
    assert all(item.owner_id == "user_b" for item in await owner_b.list_all())


async def test_conversation_filters_and_pagination_stay_owner_scoped(db_session) -> None:
    repository = ConversationRepository(db_session, "user_a")
    first = conversation("user_a", "first.mp3")
    first.title = "Buyer consultation"
    first.status = ConversationStatus.COMPLETED
    second = conversation("user_a", "second.mp3")
    second.title = "Listing review"
    await repository.add(first)
    await repository.add(second)
    await repository.add(conversation("user_b", "private.mp3"))
    await repository.commit()

    matches = await repository.list_all(search="buyer", status="COMPLETED", limit=1)
    assert [item.filename for item in matches] == ["first.mp3"]
    assert len(await repository.list_all(limit=1, offset=1)) == 1


async def test_client_filters_and_pagination_stay_owner_scoped(db_session) -> None:
    repository = ClientRepository(db_session, "user_a")
    await repository.add(
        Client(owner_id="user_a", full_name="Jane Buyer", role="buyer", email="jane@example.com")
    )
    await repository.add(Client(owner_id="user_a", full_name="Sam Seller", role="seller"))
    await repository.add(Client(owner_id="user_b", full_name="Private Buyer", role="buyer"))
    await repository.commit()

    matches = await repository.list_all(search="jane@", role="buyer", limit=1)
    assert [item.full_name for item in matches] == ["Jane Buyer"]
    assert len(await repository.list_all(limit=1, offset=1)) == 1
