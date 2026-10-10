import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.auth.tests.test_tenant_isolation import conversation
from app.conversation.enums import ConversationStatus
from app.transcription.corrections import (
    CorrectionInput,
    CorrectionRepository,
    NotesPreview,
    generate_preview,
)
from app.transcription.enums import TranscriptionStatus
from app.transcription.models import Transcript


async def test_corrections_preserve_original_and_reject_foreign_or_stale(db_session):
    c = conversation("correct_owner", "test.wav")
    c.status = ConversationStatus.COMPLETED
    db_session.add(c)
    await db_session.flush()
    cid = c.id
    db_session.add(
        Transcript(conversation_id=cid, text="ma po et", status=TranscriptionStatus.COMPLETED)
    )
    await db_session.commit()
    repo = CorrectionRepository(db_session, "correct_owner")
    saved = await repo.save(cid, CorrectionInput(text="m'ap voye", expected_version=0))
    assert saved.version == 1
    assert (
        await db_session.scalar(
            text("SELECT text FROM transcripts WHERE conversation_id=:id"), {"id": cid}
        )
        == "ma po et"
    )
    for target in (cid, uuid.uuid4()):
        with pytest.raises(HTTPException) as err:
            await CorrectionRepository(db_session, "other_owner").save(
                target, CorrectionInput(text="attack", expected_version=0)
            )
        assert err.value.status_code == 404
        await db_session.rollback()
    with pytest.raises(HTTPException) as err:
        await repo.save(cid, CorrectionInput(text="stale", expected_version=0))
    assert err.value.status_code == 409
    await db_session.rollback()
    preview = NotesPreview(summary="Will send estimate", tasks=["Send estimate"], decisions=[])
    assert (await repo.store_preview(cid, 1, preview)).preview.summary == "Will send estimate"
    assert (
        await repo.save(cid, CorrectionInput(text="new correction", expected_version=1))
    ).preview is None
    with pytest.raises(HTTPException) as err:
        await repo.store_preview(cid, 1, preview)
    assert err.value.status_code == 409
    await db_session.rollback()
    await db_session.execute(text("DELETE FROM conversations WHERE id=:id"), {"id": cid})
    await db_session.commit()
    assert await db_session.scalar(text("SELECT count(*) FROM transcript_corrections")) == 0


async def test_provider_failure_is_safe():
    provider = AsyncMock()
    provider.complete.side_effect = RuntimeError("secret source content")
    with pytest.raises(HTTPException) as err:
        await generate_preview(provider, "private")
    assert err.value.status_code == 502
    assert "secret" not in err.value.detail


def test_blank_correction_rejected():
    with pytest.raises(ValueError):
        CorrectionInput(text="  ", expected_version=0)


async def test_preview_keeps_edited_completed_work_and_drafts(db_session):
    from app.memory.drafts import DraftRepository, SaveDraft
    from app.memory.models import ActionItem, ActionStatus, Memory

    c = conversation("preserve_owner", "test.wav")
    c.status = ConversationStatus.COMPLETED
    db_session.add(c)
    await db_session.flush()
    cid = c.id
    memory = Memory(
        conversation_id=cid,
        summary="User's existing notes",
        topics=[],
        confidence=1,
        source="test",
        action_items=[ActionItem(task="User edited task", status=ActionStatus.COMPLETED)],
    )
    db_session.add_all(
        [
            memory,
            Transcript(conversation_id=cid, text="original", status=TranscriptionStatus.COMPLETED),
        ]
    )
    await db_session.commit()
    drafts = DraftRepository(db_session, "preserve_owner")
    await drafts.save(cid, "email", SaveDraft(body="My saved draft", expected_version=0))
    repo = CorrectionRepository(db_session, "preserve_owner")
    await repo.save(cid, CorrectionInput(text="Corrected facts", expected_version=0))
    await repo.store_preview(
        cid, 1, NotesPreview(summary="New suggestion", tasks=["Different task"])
    )
    assert (
        await db_session.scalar(
            text("SELECT summary FROM memories WHERE conversation_id=:id"), {"id": cid}
        )
        == "User's existing notes"
    )
    row = (
        await db_session.execute(
            text(
                "SELECT a.task,a.status FROM action_items a JOIN memories m "
                "ON m.id=a.memory_id WHERE m.conversation_id=:id"
            ),
            {"id": cid},
        )
    ).one()
    assert row.task == "User edited task" and row.status == "COMPLETED"
    assert (await drafts.get(cid, "email")).body == "My saved draft"
