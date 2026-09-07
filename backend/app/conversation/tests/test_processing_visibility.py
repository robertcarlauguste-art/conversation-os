from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.conversation.enums import ConversationSource, ConversationStatus
from app.conversation.models import Conversation
from app.conversation.repository import ConversationRepository
from app.conversation.schemas import ConversationListItem
from app.operations.repository import OperationsRepository
from app.transcription.enums import TranscriptionStatus
from app.transcription.models import Transcript


async def test_owner_scoped_metrics_match_list_stale_flags(db_session):
    owner = str(uuid4())
    now = datetime.now(UTC)
    rows = []
    for status, started in [
        (ConversationStatus.QUEUED, None),
        (ConversationStatus.PROCESSING, None),
        (ConversationStatus.PROCESSING, now),
        (ConversationStatus.FAILED, None),
        (ConversationStatus.COMPLETED, None),
    ]:
        row = Conversation(
            owner_id=owner,
            filename="test.wav",
            storage_path="private",
            mime_type="audio/wav",
            file_size=1,
            source=ConversationSource.UPLOAD,
            status=status,
            created_at=now - timedelta(days=1),
            processing_started_at=started,
        )
        db_session.add(row)
        rows.append(row)
    db_session.add(
        Conversation(
            owner_id="other-" + owner,
            filename="test.wav",
            storage_path="private",
            mime_type="audio/wav",
            file_size=1,
            status=ConversationStatus.QUEUED,
            created_at=now - timedelta(days=1),
        )
    )
    await db_session.commit()
    db_session.add(
        Transcript(
            conversation_id=rows[3].id,
            status=TranscriptionStatus.FAILED,
            error_message="legacy failure",
            text="private transcript",
        )
    )
    await db_session.commit()
    repository = ConversationRepository(db_session, owner)
    listed = [ConversationListItem.model_validate(c) for c in await repository.list_all()]
    metrics = await OperationsRepository(db_session, owner).processing_metrics(3)
    assert metrics.total == len(listed) == 5
    assert metrics.stale == sum(c.is_stale for c in listed) == 2
    for status in ["queued", "processing", "completed", "failed"]:
        assert getattr(metrics, status) == sum(c.status == status.upper() for c in listed)
    assert await repository.latest_transcript_error(rows[3].id) == "legacy failure"
    assert (
        await ConversationRepository(db_session, "other-" + owner).latest_transcript_error(
            rows[3].id
        )
        is None
    )


async def test_latest_error_is_deterministic_even_with_legacy_duplicate_rows(db_session):
    from uuid import UUID

    from sqlalchemy import text

    # Restore the constraint and remove all synthetic data when this savepoint rolls back.
    transaction = await db_session.begin_nested()
    try:
        await db_session.execute(
            text("ALTER TABLE transcripts DROP CONSTRAINT uq_transcripts_conversation_id")
        )
        owner = str(uuid4())
        conversation = Conversation(
            owner_id=owner,
            filename="test.wav",
            storage_path="private",
            mime_type="audio/wav",
            file_size=1,
        )
        db_session.add(conversation)
        await db_session.flush()
        now = datetime.now(UTC)
        for number, updated, error in [
            (1, now - timedelta(days=1), "old"),
            (2, now, "new"),
            (3, now, "tie winner"),
        ]:
            db_session.add(
                Transcript(
                    id=UUID(int=number),
                    conversation_id=conversation.id,
                    status=TranscriptionStatus.FAILED,
                    created_at=now,
                    updated_at=updated,
                    error_message=error,
                )
            )
        await db_session.flush()
        assert (
            await ConversationRepository(db_session, owner).latest_transcript_error(conversation.id)
            == "tie winner"
        )
    finally:
        await transaction.rollback()
