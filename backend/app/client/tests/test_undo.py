import asyncio
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.client.merge import inspect_merge, merge_clients
from app.client.models import Client, ClientFact, ClientMergeAudit
from app.client.tests.test_merge import pair
from app.client.undo import undo_merge
from app.conversation.models import Conversation
from app.dashboard.models import ClientFollowupAction, FollowupAction
from app.memory.models import ActionItem, Memory, Person


async def merged(session):
    a, b, c = await pair(session)
    from app.conversation.enums import ConversationStatus

    session.add(
        Conversation(
            owner_id="A",
            client_id=b,
            filename="retained.webm",
            storage_path="fake",
            mime_type="audio/webm",
            file_size=1,
            status=ConversationStatus.COMPLETED,
            client_assignment_manual=True,
        )
    )
    await session.execute(
        update(Client).where(Client.id == b).values(saved_review={"content": "target review"})
    )
    memory = Memory(conversation_id=c, summary="Original", confidence=0.8, source="test")
    session.add(memory)
    await session.flush()
    person = Person(memory_id=memory.id, client_id=a, name="Morgan", confirmed_name="Morgan Vale")
    task = ActionItem(memory_id=memory.id, task="Send estimate")
    fact = ClientFact(
        client_id=a, fact_text="Budget", source_conversation_id=c, source_memory_id=memory.id
    )
    event = ClientFollowupAction(client_id=a, action=FollowupAction.RECORD_CONTACT)
    session.add_all([person, task, fact, event])
    await session.commit()
    _, _, _, token, _ = await inspect_merge(session, "A", a, b)
    await session.rollback()
    await merge_clients(session, "A", a, b, token, "Morgan Vale")
    audit = await session.scalar(select(ClientMergeAudit).where(ClientMergeAudit.source_id == a))
    return a, b, c, audit.id


async def test_undo_restores_both_profiles_links_and_manual_flag(db_session):
    a, b, c, audit_id = await merged(db_session)
    await undo_merge(db_session, "A", audit_id)
    db_session.expire_all()
    source = await db_session.get(Client, a)
    target = await db_session.get(Client, b)
    assert source.saved_review == {"content": "old"}
    assert target.saved_review == {"content": "target review"}
    assert source.full_name == "Morgan Vail" and target.email == "keep@example.test"
    recording = await db_session.get(Conversation, c)
    assert recording.client_id == a and not recording.client_assignment_manual
    retained_recording = await db_session.scalar(
        select(Conversation).where(
            Conversation.client_id == b, Conversation.filename == "retained.webm"
        )
    )
    assert retained_recording and retained_recording.client_assignment_manual
    for model in (Person, ClientFact, ClientFollowupAction):
        assert await db_session.scalar(select(model.id).where(model.client_id == a))
    audit = await db_session.get(ClientMergeAudit, audit_id)
    assert audit.snapshot["undone_at"]
    with pytest.raises(HTTPException) as exc:
        await undo_merge(db_session, "A", audit_id)
    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "change", ["profile", "recording", "task", "unlink", "new_recording", "new_review"]
)
async def test_undo_rejects_newer_work_without_partial_restore(db_session, change):
    a, b, c, audit_id = await merged(db_session)
    if change == "profile":
        await db_session.execute(
            update(Client).where(Client.id == b).values(email="new@example.test")
        )
    elif change == "new_review":
        await db_session.execute(
            update(Client).where(Client.id == b).values(saved_review={"content": "new"})
        )
    elif change == "recording":
        await db_session.execute(
            update(Conversation).where(Conversation.id == c).values(title="New title")
        )
    elif change == "unlink":
        await db_session.execute(
            update(Conversation).where(Conversation.id == c).values(client_id=None)
        )
    elif change == "task":
        memory = await db_session.scalar(select(Memory.id).where(Memory.conversation_id == c))
        await db_session.execute(
            update(ActionItem).where(ActionItem.memory_id == memory).values(task="Edited task")
        )
    else:
        db_session.add(
            Conversation(
                owner_id="A",
                client_id=b,
                filename="new",
                storage_path="fake",
                mime_type="audio/webm",
                file_size=1,
            )
        )
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await undo_merge(db_session, "A", audit_id)
    assert exc.value.status_code == 409
    assert await db_session.get(Client, a) is None
    audit = await db_session.get(ClientMergeAudit, audit_id)
    assert not audit.snapshot.get("undone_at")


async def test_undo_foreign_missing_and_legacy_denied(db_session):
    a, b, c, audit_id = await merged(db_session)
    for key in (audit_id, uuid.uuid4()):
        with pytest.raises(HTTPException) as exc:
            await undo_merge(db_session, "B", key)
        assert (exc.value.status_code, exc.value.detail) == (404, "Merge not found.")
    audit = await db_session.get(ClientMergeAudit, audit_id)
    audit.snapshot = {k: v for k, v in audit.snapshot.items() if k != "undo_version"}
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await undo_merge(db_session, "A", audit_id)
    assert exc.value.status_code == 409
    assert await db_session.get(Client, a) is None


async def test_undo_commit_failure_is_atomic(db_session, monkeypatch):
    a, b, c, audit_id = await merged(db_session)

    async def fail():
        raise RuntimeError("commit failure")

    monkeypatch.setattr(db_session, "commit", fail)
    with pytest.raises(RuntimeError):
        await undo_merge(db_session, "A", audit_id)
    db_session.expire_all()
    assert await db_session.get(Client, a) is None
    assert (await db_session.get(Conversation, c)).client_id == b
    assert not (await db_session.get(ClientMergeAudit, audit_id)).snapshot.get("undone_at")


async def test_history_and_undo_http_are_owner_scoped(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.auth.dependencies import require_principal
    from app.auth.schemas import Principal
    from app.main import app

    a, b, c, audit_id = await merged(db_session)
    app.dependency_overrides[require_principal] = lambda: Principal(user_id="B")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            history = await http.get("/api/v1/clients/merge-history/recent")
            assert history.status_code == 200
            assert str(audit_id) not in history.text
            denied = await http.post(f"/api/v1/clients/merge-history/{audit_id}/undo")
            missing = await http.post(f"/api/v1/clients/merge-history/{uuid.uuid4()}/undo")
            assert denied.status_code == missing.status_code == 404
            assert denied.json() == missing.json()
            app.dependency_overrides[require_principal] = lambda: Principal(user_id="A")
            history = await http.get("/api/v1/clients/merge-history/recent")
            assert any(
                row["id"] == str(audit_id) and row["supports_undo"]
                for row in history.json()["data"]
            )
            assert "after_digest" not in history.text and "saved_review" not in history.text
            result = await http.post(f"/api/v1/clients/merge-history/{audit_id}/undo")
            assert result.status_code == 200
    finally:
        app.dependency_overrides.pop(require_principal, None)


async def test_new_saved_draft_blocks_undo(db_session):
    a, b, c, audit_id = await merged(db_session)
    await db_session.execute(
        text(
            "INSERT INTO followup_drafts(conversation_id,channel,subject,body,version) "
            "VALUES (:id,'email','New subject','New draft',1)"
        ),
        {"id": c},
    )
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await undo_merge(db_session, "A", audit_id)
    assert exc.value.status_code == 409
    assert await db_session.get(Client, a) is None


async def test_simultaneous_undo_only_restores_once(db_session):
    a, b, c, audit_id = await merged(db_session)
    await db_session.rollback()
    maker = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def attempt():
        async with maker() as session:
            try:
                await undo_merge(session, "A", audit_id)
                return 200
            except HTTPException as exc:
                return exc.status_code

    results = await asyncio.wait_for(asyncio.gather(attempt(), attempt()), timeout=15)
    assert sorted(results) == [200, 409]
    db_session.expire_all()
    assert (await db_session.get(Conversation, c)).client_id == a
