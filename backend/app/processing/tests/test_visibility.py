from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.conversation.schemas import ConversationDetail, ConversationListItem
from app.processing.visibility import is_stale, safe_error, stale_threshold_seconds
from app.transcription.schemas import TranscriptDetail

NOW = datetime(2026, 9, 7, tzinfo=UTC)


@pytest.mark.parametrize("status", ["QUEUED", "PROCESSING"])
def test_stale_boundary_and_missing_start(status):
    threshold = timedelta(seconds=stale_threshold_seconds())
    assert not is_stale(status, NOW - threshold, None, NOW)
    assert is_stale(status, NOW - threshold - timedelta(microseconds=1), None, NOW)


@pytest.mark.parametrize("status", ["UPLOADED", "FAILED", "COMPLETED"])
def test_terminal_and_unqueued_records_are_not_stale(status):
    assert not is_stale(status, NOW - timedelta(days=30), None, NOW)


def test_recent_attempt_on_old_upload_is_active():
    assert not is_stale("PROCESSING", NOW - timedelta(days=30), NOW - timedelta(seconds=10), NOW)


def test_long_worker_timeout_extends_threshold(monkeypatch):
    monkeypatch.setattr(
        "app.processing.visibility.get_settings",
        lambda: SimpleNamespace(processing_job_timeout_seconds=1800),
    )
    assert stale_threshold_seconds() == 1860


@pytest.mark.parametrize(
    "secret",
    [
        "Authorization: Bearer private-token",
        "https://bucket/audio?signature=secret",
        "full transcript: private words",
        "raw audio: abc123",
        "api_key=secret",
    ],
)
def test_api_error_projections_never_echo_unknown_payloads(secret):
    row = dict(
        id=uuid4(),
        title=None,
        status="FAILED",
        file_size=1,
        created_at=NOW,
        processing_error=secret,
    )
    assert secret not in ConversationListItem(**row).model_dump_json()
    detail = ConversationDetail(
        **row,
        filename="test.wav",
        mime_type="audio/wav",
        duration_seconds=None,
        source="UPLOAD",
        client_id=None,
        updated_at=NOW,
    )
    assert detail.processing_error == safe_error(secret)
    transcript = TranscriptDetail(
        id=uuid4(),
        conversation_id=row["id"],
        text=None,
        language=None,
        status="FAILED",
        error_message=secret,
        created_at=NOW,
        updated_at=NOW,
    )
    assert secret not in transcript.model_dump_json()


async def test_detail_falls_back_to_safe_transcript_error():
    from app.conversation.service import ConversationService

    row = SimpleNamespace(
        id=uuid4(),
        title=None,
        filename="test.wav",
        mime_type="audio/wav",
        file_size=1,
        duration_seconds=None,
        status="FAILED",
        source="UPLOAD",
        client_id=None,
        created_at=NOW,
        updated_at=NOW,
        processing_error=None,
    )
    service = ConversationService(
        SimpleNamespace(
            get=AsyncMock(return_value=row),
            latest_transcript_error=AsyncMock(return_value="Authorization: Bearer secret"),
        ),
        SimpleNamespace(),
        allowed_mime_types=(),
        max_upload_size_bytes=1,
    )
    detail = await service.get_conversation_detail(row.id)
    assert detail.processing_error == safe_error("unknown")
    assert "Bearer" not in detail.model_dump_json()


async def test_dashboard_counts_match_all_conversations():
    from app.dashboard.service import DashboardService

    statuses = ["QUEUED", "PROCESSING", "PROCESSING", "COMPLETED", "FAILED", "UPLOADED"]
    rows = [
        SimpleNamespace(
            id=uuid4(),
            title=None,
            status=s,
            file_size=1,
            created_at=NOW - timedelta(days=1),
            processing_started_at=NOW if i == 2 else None,
        )
        for i, s in enumerate(statuses)
    ]
    service = DashboardService(
        conversation_service=SimpleNamespace(list_conversations=AsyncMock(return_value=rows)),
        client_service=SimpleNamespace(list_client_profiles=AsyncMock(return_value=[])),
        clock=lambda: NOW,
    )
    dashboard = await service.get_dashboard()
    assert dashboard.overview.model_dump() == dict(
        clients=0, conversations=6, queued=1, processing=2, completed=1, failed=1, stale=2
    )


async def test_operations_query_scopes_owner_and_counts_stale():
    from unittest.mock import MagicMock

    from sqlalchemy.dialects import postgresql

    from app.operations.repository import OperationsRepository

    result = MagicMock()
    result.one.return_value = (6, 1, 2, 1, 1, 0, None, 2)
    session = SimpleNamespace(execute=AsyncMock(return_value=result))
    metrics = await OperationsRepository(session, "owner-a").processing_metrics(3)
    query = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "conversations.owner_id =" in str(query)
    assert "owner-a" in query.params.values()
    assert "coalesce(conversations.processing_started_at, conversations.created_at)" in str(query)
    assert metrics.stale == 2


async def test_transcription_logs_no_provider_payload_or_transcript(caplog):
    import logging

    from app.providers.transcription_provider import TranscriptionResult
    from app.transcription.models import Transcript
    from app.transcription.service import TranscriptionService

    caplog.set_level(logging.INFO)
    transcript = Transcript(conversation_id=uuid4())
    repository = SimpleNamespace(
        get_by_conversation_id=AsyncMock(return_value=transcript), commit=AsyncMock()
    )
    provider = SimpleNamespace(
        transcribe=AsyncMock(
            return_value=TranscriptionResult(text="private transcript marker", language="en")
        )
    )
    storage = SimpleNamespace(read=AsyncMock(return_value=b"private audio marker"))
    service = TranscriptionService(repository, provider, storage)
    await service.transcribe(
        conversation_id=transcript.conversation_id, storage_path="private", filename="test.wav"
    )
    assert "private transcript marker" not in caplog.text
    assert "private audio marker" not in caplog.text
    transcript.status = "FAILED"
    provider.transcribe.side_effect = RuntimeError("Authorization: Bearer private-secret")
    with pytest.raises(RuntimeError):
        await service.transcribe(
            conversation_id=transcript.conversation_id, storage_path="private", filename="test.wav"
        )
    assert "private-secret" not in caplog.text
    assert "private-secret" not in transcript.error_message


@pytest.mark.parametrize("naive_since", [True, False])
@pytest.mark.parametrize("naive_now", [True, False])
@pytest.mark.parametrize("status", ["QUEUED", "PROCESSING"])
def test_stale_normalizes_both_clock_and_stored_timestamps(naive_since, naive_now, status):
    from datetime import timezone

    since = NOW - timedelta(seconds=stale_threshold_seconds() + 1)
    since = (
        since.replace(tzinfo=None)
        if naive_since
        else since.astimezone(timezone(timedelta(hours=-4)))
    )
    observed = (
        NOW.replace(tzinfo=None) if naive_now else NOW.astimezone(timezone(timedelta(hours=5)))
    )
    assert is_stale(status, since, since if status == "PROCESSING" else None, observed)
    assert not is_stale(status, observed, observed, observed)


async def test_detail_api_uses_service_without_repository_access():
    from app.conversation.api import get_conversation

    detail = ConversationDetail(
        id=uuid4(),
        title=None,
        filename="test.wav",
        mime_type="audio/wav",
        file_size=1,
        duration_seconds=None,
        status="FAILED",
        source="UPLOAD",
        client_id=None,
        created_at=NOW,
        updated_at=NOW,
    )
    service = SimpleNamespace(get_conversation_detail=AsyncMock(return_value=detail))
    assert (await get_conversation(detail.id, service)).data == detail


@pytest.mark.parametrize(
    "body", ["Authorization: Bearer private-secret", '{"summary":"private-secret"}']
)
async def test_memory_errors_and_logs_omit_provider_content(body, caplog):
    import logging
    import traceback

    from app.memory.service import ExtractionError, MemoryService

    caplog.set_level(logging.INFO)
    provider = SimpleNamespace(complete=AsyncMock(return_value=SimpleNamespace(content=body)))
    service = MemoryService(SimpleNamespace(), provider, model="test")
    with pytest.raises(ExtractionError) as failure:
        await service.extract_and_persist(
            conversation_id=uuid4(), transcript_text="private transcript"
        )
    assert "private-secret" not in str(failure.value)
    assert "private-secret" not in "".join(traceback.format_exception(failure.value))
    assert "private-secret" not in caplog.text
    assert "private transcript" not in caplog.text


async def test_upload_error_and_logs_omit_storage_body_and_filename(caplog):
    import logging

    from app.conversation.service import ConversationService

    caplog.set_level(logging.INFO)
    service = ConversationService(
        SimpleNamespace(),
        SimpleNamespace(save=AsyncMock(side_effect=RuntimeError("Authorization: private-secret"))),
        allowed_mime_types=("audio/wav",),
        max_upload_size_bytes=100,
    )
    with pytest.raises(RuntimeError) as failure:
        await service.upload(
            filename="private-secret.wav", content_type="audio/wav", content=b"private audio"
        )
    assert "private-secret" not in str(failure.value)
    # Suppress the provider exception context from production tracebacks.
    assert failure.value.__suppress_context__
    assert "storage and database availability" in str(failure.value)
    assert "private-secret" not in caplog.text
