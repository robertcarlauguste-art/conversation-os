from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from arq.worker import Retry

from app.processing import worker


def _session_context(session: AsyncMock) -> MagicMock:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


async def test_failed_attempt_rolls_back_before_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(side_effect=RuntimeError("temporary"))
    orchestrator.mark_failed = AsyncMock()
    settings = MagicMock(processing_max_tries=3)

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "build_storage_backend", MagicMock())
    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: _session_context(session))
    monkeypatch.setattr(
        worker, "build_conversation_processing_orchestrator", lambda *args: orchestrator
    )

    with pytest.raises(Retry):
        await worker.process_conversation({"job_try": 1}, str(uuid4()), "owner")

    session.rollback.assert_awaited_once()
    orchestrator.mark_failed.assert_not_awaited()


async def test_exhausted_attempt_is_marked_failed_after_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    events: list[str] = []
    session.rollback.side_effect = lambda: events.append("rollback")
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(side_effect=RuntimeError("permanent"))

    async def mark_failed(*args: object) -> None:
        events.append("failed")

    orchestrator.mark_failed = AsyncMock(side_effect=mark_failed)
    settings = MagicMock(processing_max_tries=3)
    conversation_id = uuid4()

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "build_storage_backend", MagicMock())
    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: _session_context(session))
    monkeypatch.setattr(
        worker, "build_conversation_processing_orchestrator", lambda *args: orchestrator
    )

    with pytest.raises(RuntimeError, match="permanent"):
        await worker.process_conversation({"job_try": 3}, str(conversation_id), "owner")

    assert events == ["rollback", "failed"]
    orchestrator.mark_failed.assert_awaited_once_with(conversation_id, "permanent")
