import asyncio
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth.tests.test_tenant_isolation import conversation
from app.memory.drafts import DraftRepository, SaveDraft


async def test_saved_drafts_isolation_conflicts_channels_and_deletion(db_session):
    records = [conversation(owner, owner + ".wav") for owner in ("draft_a", "draft_b")]
    db_session.add_all(records)
    await db_session.commit()
    ids = [record.id for record in records]
    for index, owner in enumerate(("draft_a", "draft_b")):
        repo = DraftRepository(db_session, owner)
        assert await repo.get(ids[index], "email") is None
        saved = await repo.save(
            ids[index],
            "email",
            SaveDraft(subject="Subject", body=owner + " original", expected_version=0),
        )
        assert saved.version == 1
        for foreign in (ids[1 - index], uuid.uuid4()):
            for operation in (
                repo.get(foreign, "email"),
                repo.save(foreign, "email", SaveDraft(body="attack", expected_version=0)),
            ):
                with pytest.raises(HTTPException) as error:
                    await operation
                assert (error.value.status_code, error.value.detail) == (
                    404,
                    "Conversation not found.",
                )
                await db_session.rollback()
        with pytest.raises(HTTPException) as error:
            await repo.save(ids[index], "email", SaveDraft(body="stale", expected_version=0))
        assert error.value.status_code == 409
        await db_session.rollback()
        assert (await repo.get(ids[index], "email")).body == owner + " original"
        updated = await repo.save(ids[index], "email", SaveDraft(body="edited", expected_version=1))
        assert updated.version == 2
        await repo.save(
            ids[index], "text", SaveDraft(subject="ignored", body="short", expected_version=0)
        )
        assert (await repo.get(ids[index], "text")).subject == ""
        assert (await repo.get(ids[index], "email")).body == "edited"
    await db_session.execute(text("DELETE FROM conversations WHERE id=:id"), {"id": ids[0]})
    await db_session.commit()
    assert (
        await db_session.scalar(
            text("SELECT count(*) FROM followup_drafts WHERE conversation_id=:id"), {"id": ids[0]}
        )
        == 0
    )
    assert (
        await db_session.scalar(
            text("SELECT count(*) FROM followup_drafts WHERE conversation_id=:id"), {"id": ids[1]}
        )
        == 2
    )


def test_blank_body_rejected():
    with pytest.raises(ValueError):
        SaveDraft(body="   ", expected_version=0)


async def test_simultaneous_first_saves_do_not_overwrite(db_session):
    record = conversation("concurrent_owner", "draft.wav")
    db_session.add(record)
    await db_session.commit()
    conversation_id = record.id
    maker = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def save(message):
        async with maker() as session:
            try:
                saved = await DraftRepository(session, "concurrent_owner").save(
                    conversation_id, "email", SaveDraft(body=message, expected_version=0)
                )
                return saved.body
            except HTTPException as error:
                assert error.status_code == 409
                return "conflict"

    results = await asyncio.gather(save("first tab"), save("second tab"))
    assert results.count("conflict") == 1
    persisted = await DraftRepository(db_session, "concurrent_owner").get(conversation_id, "email")
    assert persisted.version == 1
    assert persisted.body in results
