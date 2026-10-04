import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.client.merge import inspect_merge, merge_clients
from app.client.models import Client, ClientMergeAudit
from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation


async def pair(session):
    a = Client(full_name="Morgan Vail", owner_id="A", saved_review={"content": "old"})
    b = Client(full_name="Morgan Vale", owner_id="A", email="keep@example.test")
    session.add_all([a, b])
    await session.flush()
    c = Conversation(
        owner_id="A",
        client_id=a.id,
        filename="test.webm",
        storage_path="fake",
        mime_type="audio/webm",
        file_size=10,
        source=ConversationSource.UPLOAD,
        status=ConversationStatus.COMPLETED,
    )
    session.add(c)
    await session.commit()
    return a.id, b.id, c.id


async def test_merge_preserves_recording_and_archives_identity(db_session):
    a, b, c = await pair(db_session)
    _, _, _, token, counts = await inspect_merge(db_session, "A", a, b)
    assert counts["conversations"] == 1
    await db_session.rollback()
    await merge_clients(db_session, "A", a, b, token, "Morgan Vale")
    db_session.expire_all()
    recording = await db_session.get(Conversation, c)
    assert recording.client_id == b and recording.client_assignment_manual
    assert recording.filename == "test.webm"
    assert await db_session.get(Client, a) is None
    retained = await db_session.get(Client, b)
    assert retained.email == "keep@example.test"
    audit = await db_session.scalar(select(ClientMergeAudit).where(ClientMergeAudit.source_id == a))
    assert audit.snapshot["source"]["saved_review"] == {"content": "old"}
    assert audit.snapshot["links"]["conversations"][str(c)] == str(a)


@pytest.mark.parametrize("actor", ["B", "C"])
async def test_foreign_and_missing_pairs_are_indistinguishable(db_session, actor):
    a, b, _ = await pair(db_session)
    for source in (a, uuid.uuid4()):
        with pytest.raises(HTTPException) as exc:
            await merge_clients(db_session, actor, source, b, "x" * 64, "Morgan Vale")
        assert (exc.value.status_code, exc.value.detail) == (404, "Client pair not found.")
    assert await db_session.get(Client, a) is not None


async def test_stale_preview_and_same_record_do_not_mutate(db_session):
    a, b, c = await pair(db_session)
    _, _, _, token, _ = await inspect_merge(db_session, "A", a, b)
    target = await db_session.get(Client, b)
    target.email = "changed@example.test"
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await merge_clients(db_session, "A", a, b, token, "Morgan Vale")
    assert exc.value.status_code == 409
    assert (await db_session.get(Conversation, c)).client_id == a
    with pytest.raises(HTTPException) as exc:
        await merge_clients(db_session, "A", a, a, token, "Morgan Vail")
    assert exc.value.status_code == 404


async def test_failure_rolls_back_all_moves(db_session, monkeypatch):
    a, b, c = await pair(db_session)
    _, _, _, token, _ = await inspect_merge(db_session, "A", a, b)
    await db_session.rollback()

    async def fail():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError):
        await merge_clients(db_session, "A", a, b, token, "Morgan Vale")
    assert (await db_session.get(Conversation, c)).client_id == a
    assert await db_session.get(Client, a) is not None
    assert (
        await db_session.scalar(select(ClientMergeAudit).where(ClientMergeAudit.source_id == a))
        is None
    )


async def test_merge_preserves_people_facts_and_followup_history(db_session):
    from app.client.models import ClientFact
    from app.dashboard.models import ClientFollowupAction, FollowupAction
    from app.memory.models import Memory, Person

    a, b, c = await pair(db_session)
    memory = Memory(conversation_id=c, summary="Original summary", confidence=0.8, source="test")
    db_session.add(memory)
    await db_session.flush()
    person = Person(
        memory_id=memory.id, client_id=a, name="Morgan Vail", confirmed_name="Morgan Vale"
    )
    fact = ClientFact(
        client_id=a, fact_text="Original fact", source_conversation_id=c, source_memory_id=memory.id
    )
    event = ClientFollowupAction(client_id=a, action=FollowupAction.RECORD_CONTACT)
    db_session.add_all([person, fact, event])
    await db_session.commit()
    ids = person.id, fact.id, event.id
    _, _, _, token, _ = await inspect_merge(db_session, "A", a, b)
    await db_session.rollback()
    await merge_clients(db_session, "A", a, b, token, "Morgan Vale")
    db_session.expire_all()
    person = await db_session.get(Person, ids[0])
    fact = await db_session.get(ClientFact, ids[1])
    event = await db_session.get(ClientFollowupAction, ids[2])
    assert person.client_id == fact.client_id == event.client_id == b
    assert person.name == "Morgan Vail" and person.confirmed_name == "Morgan Vale"
    assert fact.fact_text == "Original fact" and fact.source_conversation_id == c
    assert event.action == FollowupAction.RECORD_CONTACT


async def test_api_requires_owned_pair_and_confirmation(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.auth.dependencies import require_principal
    from app.auth.schemas import Principal
    from app.main import app

    a, b, _ = await pair(db_session)
    app.dependency_overrides[require_principal] = lambda: Principal(user_id="B")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            foreign = await http.post(
                f"/api/v1/clients/{a}/merge-preview", json={"target_id": str(b)}
            )
            missing = await http.post(
                f"/api/v1/clients/{uuid.uuid4()}/merge-preview", json={"target_id": str(b)}
            )
            assert foreign.status_code == missing.status_code == 404
            assert foreign.json() == missing.json()
            app.dependency_overrides[require_principal] = lambda: Principal(user_id="A")
            preview = await http.post(
                f"/api/v1/clients/{a}/merge-preview", json={"target_id": str(b)}
            )
            assert preview.status_code == 200
            denied = await http.post(
                f"/api/v1/clients/{a}/merge",
                json={
                    "target_id": str(b),
                    "expected_token": preview.json()["data"]["token"],
                    "confirmed_name": "wrong",
                },
            )
            assert denied.status_code == 409
    finally:
        app.dependency_overrides.pop(require_principal, None)
