import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.client import review
from app.providers.ai_provider import AICompletionResult


def setup(monkeypatch, responses):
    origin, later, action = (str(uuid.uuid4()) for _ in range(3))
    payload = {
        "open_actions": [{"id": action, "source_conversation_id": origin}],
        "sources": [
            {"id": origin, "uploaded_at": "2026-09-01", "text": "Send listings"},
            {"id": later, "uploaded_at": "2026-09-02", "text": "Sent listings"},
        ],
    }
    context = (
        None,
        [1, 2],
        {later: "Sent listings"},
        {action: "Send listings"},
        json.dumps(payload),
        "fingerprint",
    )
    monkeypatch.setattr(review, "review_context", AsyncMock(return_value=context))
    repository = SimpleNamespace(
        session=SimpleNamespace(execute=AsyncMock()), commit=AsyncMock(), owner_id="test-owner"
    )
    good = AICompletionResult(
        content=json.dumps(
            {
                "assessments": [
                    {
                        "action_id": action,
                        "outcome": "completed",
                        "source_conversation_id": later,
                        "quote": "Sent listings",
                    }
                ]
            }
        ),
        model="test",
    )
    details = AICompletionResult(content='{"details":[]}', model="test")
    mapping = {
        "details": details,
        "good": good,
        "bad": AICompletionResult(content="PRIVATE RESPONSE", model="test"),
        "provider": RuntimeError("PRIVATE PROVIDER ERROR"),
    }
    provider = SimpleNamespace(complete=AsyncMock(side_effect=[mapping[x] for x in responses]))
    return repository, provider


async def test_recovers_once_without_duplicate_suggestions(monkeypatch, caplog):
    repo, provider = setup(monkeypatch, ["details", "bad", "details", "good"])
    result = await review.generate_review(repo, uuid.uuid4(), provider)
    assert len(result.completed_actions) == 1
    assert provider.complete.await_count == 4
    repo.session.execute.assert_awaited_once()
    repo.commit.assert_awaited_once()
    assert "stage=completion category=format attempt=1 retry=True" in caplog.text
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize(
    "responses,calls",
    [
        (["bad", "bad"], 2),
        (["details", "bad", "details", "bad"], 4),
        (["provider"], 1),
    ],
)
async def test_failure_preserves_saved_review_and_never_writes_tasks(
    monkeypatch, caplog, responses, calls
):
    repo, provider = setup(monkeypatch, responses)
    with pytest.raises(HTTPException) as error:
        await review.generate_review(repo, uuid.uuid4(), provider)
    assert error.value.status_code == 502
    assert "saved review and tasks are unchanged" in error.value.detail
    assert provider.complete.await_count == calls
    repo.session.execute.assert_not_awaited()
    repo.commit.assert_not_awaited()
    assert "PRIVATE" not in caplog.text


async def test_evidence_failure_retries_once(monkeypatch, caplog):
    repo, provider = setup(monkeypatch, ["details", "good", "details", "good"])
    assess = AsyncMock(side_effect=[ValueError("PRIVATE QUOTE"), []])
    monkeypatch.setattr(review, "assess_completions", assess)
    # Both provider calls now serve the detail stage.
    provider.complete.side_effect = [AICompletionResult(content='{"details":[]}', model="test")] * 2
    result = await review.generate_review(repo, uuid.uuid4(), provider)
    assert result.completed_actions == []
    assert assess.await_count == 2
    assert "category=evidence" in caplog.text
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize("changed_field", [4, 5])
async def test_context_change_during_generation_rejects_stale_review(monkeypatch, changed_field):
    repo, provider = setup(monkeypatch, ["details", "good"])
    original = review.review_context.return_value
    changed = list(original)
    changed[changed_field] = "changed source or open task context"

    async def complete(*args, **kwargs):
        # Simulate another request changing sources/tasks during the AI wait.
        review.review_context.return_value = tuple(changed)
        return AICompletionResult(content='{"details":[]}', model="test")

    provider.complete.side_effect = complete
    monkeypatch.setattr(review, "assess_completions", AsyncMock(return_value=[]))
    with pytest.raises(HTTPException) as error:
        await review.generate_review(repo, uuid.uuid4(), provider)
    assert error.value.status_code == 409
    assert "Refresh and try again" in error.value.detail
    repo.session.execute.assert_not_awaited()
    repo.commit.assert_not_awaited()
