from datetime import UTC, datetime, timedelta

from app.conversation.enums import ConversationStatus
from app.conversation.models import Conversation
from app.monitoring.repository import processing_counts


async def test_operator_aggregates_recent_queue_and_failure_window(db_session):
    now = datetime.now(UTC)
    provider_error = "Memory extraction failed. Check the extraction provider configuration."
    # Different owners, old uploads, but only one actually stale queue entry.
    for owner, status, updated, started, error in [
        ("a", "QUEUED", now, None, None),
        ("b", "QUEUED", now - timedelta(hours=1), None, None),
        ("a", "PROCESSING", now, now, provider_error),
        ("b", "FAILED", now, now, provider_error),
        ("b", "FAILED", now - timedelta(days=2), now, provider_error),
    ]:
        db_session.add(
            Conversation(
                owner_id=owner,
                filename="private.wav",
                storage_path="private",
                mime_type="audio/wav",
                file_size=1,
                status=ConversationStatus(status),
                created_at=now - timedelta(days=3),
                updated_at=updated,
                processing_started_at=started,
                processing_error=error,
            )
        )
    await db_session.commit()
    counts = await processing_counts(db_session.bind, 900, 900)
    assert counts == {"failed": 2, "stalled": 1, "provider_failures": 2}
