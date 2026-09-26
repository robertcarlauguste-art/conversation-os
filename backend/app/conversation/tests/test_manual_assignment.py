import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.client.schemas import ClientCreate
from app.conversation.service import ConversationNotFoundError, ConversationService
from app.orchestrator.conversation_processing import ConversationProcessingOrchestrator


@pytest.mark.parametrize("client_id", [uuid.uuid4(), None])
async def test_manual_assignment_skips_identity_guessing(client_id):
    conversations = SimpleNamespace(
        get_conversation=AsyncMock(
            return_value=SimpleNamespace(client_assignment_manual=True, client_id=client_id)
        ),
        update_client=AsyncMock(),
    )
    clients = SimpleNamespace(find_or_create=AsyncMock(), record_facts=AsyncMock())
    memory = SimpleNamespace(link_person_to_client=AsyncMock())
    orchestrator = ConversationProcessingOrchestrator(conversations, None, memory, clients)
    # Even a transcript with a spelling variant must not create or reassign a client.
    await orchestrator._reconcile_people_to_clients(
        uuid.uuid4(), SimpleNamespace(people=[SimpleNamespace(name="Morgan Vail")])
    )
    clients.find_or_create.assert_not_awaited()
    conversations.update_client.assert_not_awaited()
    memory.link_person_to_client.assert_not_awaited()


async def test_foreign_or_missing_upload_client_rejected_before_storage():
    repository = SimpleNamespace(owns_client=AsyncMock(return_value=False))
    storage = SimpleNamespace(save=AsyncMock())
    service = ConversationService(
        repository, storage, allowed_mime_types=("audio/wav",), max_upload_size_bytes=100
    )
    with pytest.raises(ConversationNotFoundError, match="Client not found"):
        await service.upload(
            filename="test.wav",
            content_type="audio/wav",
            content=b"audio",
            client_id=uuid.uuid4(),
        )
    storage.save.assert_not_awaited()


def test_manual_client_name_is_trimmed_and_cannot_set_owner():
    assert ClientCreate(full_name="  Morgan Vale  ").full_name == "Morgan Vale"
    for payload in ({"full_name": "  "}, {"full_name": "Morgan", "owner_id": "other"}):
        with pytest.raises(ValidationError):
            ClientCreate.model_validate(payload)
