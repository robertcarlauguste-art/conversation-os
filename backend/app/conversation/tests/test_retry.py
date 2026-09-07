import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth.dependencies import require_principal
from app.auth.schemas import Principal
from app.conversation.api import get_storage_backend
from app.conversation.enums import ConversationStatus
from app.conversation.repository import ConversationRepository
from app.conversation.service import (
    ConversationRetryConflict,
    ConversationRetryUnavailable,
    ConversationService,
)
from app.conversation.tests.test_repository import _make_conversation
from app.main import app


def service(session, storage, owner="dev_user"):
    return ConversationService(
        ConversationRepository(session, owner),
        storage,
        allowed_mime_types=("audio/mpeg",),
        max_upload_size_bytes=1024,
    )


@pytest.fixture
async def failed(db_session):
    row = _make_conversation(
        status=ConversationStatus.FAILED,
        processing_attempts=3,
        processing_error="Processing failed.",
        processing_started_at=datetime.now(UTC),
        processing_completed_at=datetime.now(UTC),
    )
    db_session.add(row)
    await db_session.commit()
    id_ = row.id
    yield row
    await db_session.rollback()
    await ConversationRepository(db_session).delete_by_id(id_)


async def test_retry_preserves_history_and_rejects_repeat(db_session, storage_backend, failed):
    enqueue = AsyncMock()
    previous = (failed.storage_path, failed.processing_started_at, failed.created_at)
    svc = service(db_session, storage_backend)
    result = await svc.retry_conversation(failed.id, enqueue)
    assert result.status == ConversationStatus.QUEUED
    assert result.processing_attempts == 3
    assert result.processing_error is None and result.processing_completed_at is None
    assert (result.storage_path, result.processing_started_at, result.created_at) == previous
    id_ = result.id
    with pytest.raises(ConversationRetryConflict):
        await svc.retry_conversation(id_, enqueue)
    enqueue.assert_awaited_once_with(id_, 3)


@pytest.mark.parametrize("failure", ["enqueue", "commit"])
async def test_retry_rolls_back(db_session, storage_backend, failed, monkeypatch, failure):
    svc = service(db_session, storage_backend)
    id_ = failed.id
    if failure == "commit":
        monkeypatch.setattr(
            svc.repository, "commit", AsyncMock(side_effect=RuntimeError("private-secret"))
        )
    enqueue = AsyncMock(
        side_effect=RuntimeError("private-secret") if failure == "enqueue" else None
    )
    with pytest.raises(ConversationRetryUnavailable, match="Retry could not be queued"):
        await svc.retry_conversation(id_, enqueue)
    row = await svc.get_conversation(id_)
    assert row.status == ConversationStatus.FAILED
    assert row.processing_attempts == 3
    assert row.processing_completed_at is not None
    assert row.processing_error == "Processing failed."


async def test_concurrent_retries_enqueue_once(db_session, storage_backend, failed):
    maker = async_sessionmaker(db_session.bind, expire_on_commit=False)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []
    id_ = failed.id

    async def enqueue(*args):
        calls.append(args)
        entered.set()
        await release.wait()

    async with maker() as a, maker() as b:
        first = asyncio.create_task(service(a, storage_backend).retry_conversation(id_, enqueue))
        await asyncio.wait_for(entered.wait(), 5)
        second = asyncio.create_task(service(b, storage_backend).retry_conversation(id_, enqueue))
        release.set()
        results = await asyncio.wait_for(asyncio.gather(first, second, return_exceptions=True), 10)
    assert len(calls) == 1
    assert sum(isinstance(result, ConversationRetryConflict) for result in results) == 1


@pytest.mark.parametrize("status", list(ConversationStatus))
async def test_retry_endpoint_states(db_session, storage_backend, failed, monkeypatch, status):
    failed.status = status
    await db_session.commit()
    enqueue = AsyncMock()
    monkeypatch.setattr("app.conversation.api.enqueue_conversation_retry", enqueue)
    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{failed.id}/retry")
        assert response.status_code == (200 if status == ConversationStatus.FAILED else 409)
        assert enqueue.await_count == (1 if status == ConversationStatus.FAILED else 0)
    finally:
        app.dependency_overrides.clear()


async def test_retry_other_owner_and_missing_are_not_found(storage_backend, failed, monkeypatch):
    enqueue = AsyncMock()
    monkeypatch.setattr("app.conversation.api.enqueue_conversation_retry", enqueue)
    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    app.dependency_overrides[require_principal] = lambda: Principal(user_id="other_user")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for id_ in (failed.id, uuid4()):
                response = await client.post(f"/api/v1/conversations/{id_}/retry")
                assert response.status_code == 404
        enqueue.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()


async def test_retry_requires_authentication(storage_backend, monkeypatch):
    from types import SimpleNamespace

    from app.core.config import Settings, get_settings

    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    app.dependency_overrides[get_settings] = lambda: Settings(
        auth_enabled=True, clerk_secret_key="sk_test_example"
    )
    monkeypatch.setattr(
        "app.auth.dependencies.Clerk.authenticate_request",
        lambda *args, **kwargs: SimpleNamespace(is_authenticated=False, payload=None),
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{uuid4()}/retry")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("transcript_status", ["FAILED", "COMPLETED"])
async def test_retry_worker_completes_reusing_transcript(
    db_session, storage_backend, failed, monkeypatch, transcript_status
):
    from sqlalchemy import func, select

    from app.conversation.tests.test_api import _patch_providers_with_fakes
    from app.processing import worker
    from app.transcription.enums import TranscriptionStatus
    from app.transcription.models import Transcript

    failed.storage_path = await storage_backend.save(filename="test.mp3", content=b"fake audio")
    original = Transcript(
        conversation_id=failed.id,
        status=TranscriptionStatus(transcript_status),
        text="Already transcribed" if transcript_status == "COMPLETED" else None,
    )
    db_session.add(original)
    await db_session.commit()
    id_, transcript_id = failed.id, original.id
    await service(db_session, storage_backend).retry_conversation(id_, AsyncMock())
    _patch_providers_with_fakes(monkeypatch)
    monkeypatch.setattr(worker, "build_storage_backend", lambda settings: storage_backend)
    monkeypatch.setattr(
        worker, "AsyncSessionLocal", async_sessionmaker(db_session.bind, expire_on_commit=False)
    )
    await worker.process_conversation({"job_try": 1}, str(id_), "dev_user", 3)
    await db_session.refresh(failed)
    await db_session.refresh(original)
    assert failed.status == ConversationStatus.COMPLETED
    assert failed.processing_attempts == 4
    assert original.id == transcript_id
    assert original.status == TranscriptionStatus.COMPLETED
    if transcript_status == "COMPLETED":
        assert original.text == "Already transcribed"
    assert (
        await db_session.scalar(
            select(func.count()).select_from(Transcript).where(Transcript.conversation_id == id_)
        )
        == 1
    )
    await db_session.rollback()
    # A duplicate delivery cannot increment attempts or run the pipeline again.
    await worker.process_conversation({"job_try": 1}, str(id_), "dev_user", 3)
    await db_session.refresh(failed)
    assert failed.processing_attempts == 4


async def test_retry_worker_exhausts_without_allowing_manual_backoff_retry(
    db_session, storage_backend, failed, monkeypatch
):
    from arq.worker import Retry

    from app.conversation.tests.test_api import _patch_providers_with_fakes
    from app.core.config import Settings
    from app.processing import worker
    from app.transcription.tests.test_service import FailingTranscriptionProvider

    failed.storage_path = await storage_backend.save(filename="test.mp3", content=b"fake audio")
    await db_session.commit()
    id_ = failed.id
    await service(db_session, storage_backend).retry_conversation(id_, AsyncMock())
    _patch_providers_with_fakes(monkeypatch)
    monkeypatch.setattr(
        "app.orchestrator.dependencies.get_transcription_provider",
        lambda settings: FailingTranscriptionProvider(),
    )
    monkeypatch.setattr(worker, "get_settings", lambda: Settings(processing_max_tries=2))
    monkeypatch.setattr(worker, "build_storage_backend", lambda settings: storage_backend)
    monkeypatch.setattr(
        worker, "AsyncSessionLocal", async_sessionmaker(db_session.bind, expire_on_commit=False)
    )
    with pytest.raises(Retry):
        await worker.process_conversation({"job_try": 1}, str(id_), "dev_user", 3)
    await db_session.refresh(failed)
    assert failed.status == ConversationStatus.PROCESSING
    assert failed.processing_completed_at is None
    with pytest.raises(ConversationRetryConflict):
        await service(db_session, storage_backend).retry_conversation(id_, AsyncMock())
    with pytest.raises(RuntimeError, match="Transcription failed"):
        await worker.process_conversation({"job_try": 2}, str(id_), "dev_user", 3)
    await db_session.refresh(failed)
    assert failed.status == ConversationStatus.FAILED
    assert failed.processing_attempts == 5
    assert failed.processing_completed_at is not None
    assert "Transcription failed" in failed.processing_error


async def test_retry_contains_rollback_failure(db_session, storage_backend, failed, monkeypatch):
    import traceback

    svc = service(db_session, storage_backend)
    monkeypatch.setattr(
        svc.repository, "rollback", AsyncMock(side_effect=RuntimeError("private-secret"))
    )
    enqueue = AsyncMock(side_effect=RuntimeError("provider-body"))
    with pytest.raises(ConversationRetryUnavailable) as failure:
        await svc.retry_conversation(failed.id, enqueue)
    formatted = "".join(traceback.format_exception(failure.value))
    assert "private-secret" not in formatted
    assert "provider-body" not in formatted


async def test_retry_api_dispatch_failure_is_safe(db_session, storage_backend, failed, monkeypatch):
    monkeypatch.setattr(
        "app.conversation.api.enqueue_conversation_retry",
        AsyncMock(side_effect=RuntimeError("private-provider-body")),
    )
    app.dependency_overrides[get_storage_backend] = lambda: storage_backend
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{failed.id}/retry")
        assert response.status_code == 503
        assert "private-provider-body" not in response.text
        await db_session.refresh(failed)
        assert failed.status == ConversationStatus.FAILED
    finally:
        app.dependency_overrides.clear()


async def test_retry_worker_setup_exhaustion_is_failed(
    db_session, storage_backend, failed, monkeypatch
):
    from app.core.config import Settings
    from app.processing import worker

    id_ = failed.id
    await service(db_session, storage_backend).retry_conversation(id_, AsyncMock())
    monkeypatch.setattr(worker, "get_settings", lambda: Settings(processing_max_tries=1))
    monkeypatch.setattr(
        worker, "AsyncSessionLocal", async_sessionmaker(db_session.bind, expire_on_commit=False)
    )
    monkeypatch.setattr(
        worker,
        "build_storage_backend",
        lambda settings: (_ for _ in ()).throw(RuntimeError("private setup body")),
    )
    with pytest.raises(RuntimeError, match="Check provider configuration"):
        await worker.process_conversation({"job_try": 1}, str(id_), "dev_user", 3)
    await db_session.refresh(failed)
    assert failed.status == ConversationStatus.FAILED
    assert failed.processing_attempts == 3
    assert failed.processing_completed_at is not None
    assert "private" not in failed.processing_error
