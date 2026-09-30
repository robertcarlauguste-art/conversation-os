import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.auth.schemas import Principal
from app.auth.tests.test_tenant_isolation import conversation
from app.conversation.enums import ConversationStatus
from app.memory.api import prepare_followup
from app.memory.followup import FollowupRequest, generate_draft, selected_facts
from app.memory.models import ActionItem, ActionStatus, Memory
from app.providers.ai_provider import AICompletionResult


async def test_owner_and_nested_task_isolation_before_provider_or_charge(db_session, monkeypatch):
    from app.memory import api

    provider = SimpleNamespace(
        complete=AsyncMock(
            return_value=AICompletionResult(
                content='{"subject":"Next steps","body":"Please review our next steps."}',
                model="fake",
            )
        )
    )
    monkeypatch.setattr(api, "get_ai_provider", lambda _: provider)
    charge = AsyncMock()
    monkeypatch.setattr(api.UsageService, "consume_ai", charge)
    settings = SimpleNamespace(anthropic_api_key="test", pilot_limits_enabled=True)
    records = []
    for owner in ("followup_a", "followup_b"):
        record = conversation(owner, owner + ".wav")
        record.status = ConversationStatus.COMPLETED
        db_session.add(record)
        await db_session.flush()
        memory = Memory(
            conversation_id=record.id,
            summary=owner + " private summary",
            confidence=0.8,
            source="test",
        )
        memory.action_items = [
            ActionItem(task="Send proposal", owner="Taylor", status=ActionStatus.OPEN)
        ]
        db_session.add(memory)
        await db_session.flush()
        records.append((record.id, memory.action_items[0].id))
    await db_session.commit()
    for index, owner in enumerate(("followup_a", "followup_b")):
        own, foreign = records[index], records[1 - index]
        for target in (foreign[0], uuid.uuid4()):
            with pytest.raises(HTTPException) as error:
                await prepare_followup(
                    target,
                    FollowupRequest(channel="email", include_summary=True),
                    Principal(user_id=owner),
                    db_session,
                    settings,
                )
            assert (error.value.status_code, error.value.detail) == (
                404,
                "Conversation results not found.",
            )
        with pytest.raises(HTTPException) as error:
            await prepare_followup(
                own[0],
                FollowupRequest(channel="email", action_ids=[foreign[1]]),
                Principal(user_id=owner),
                db_session,
                settings,
            )
        assert error.value.status_code == 404
    provider.complete.assert_not_called()
    charge.assert_not_called()
    await prepare_followup(
        records[0][0],
        FollowupRequest(channel="email", action_ids=[records[0][1]]),
        Principal(user_id="followup_a"),
        db_session,
        settings,
    )
    charge.assert_awaited_once()
    sent = provider.complete.call_args.args[0][0].content
    assert "private summary" not in sent
    assert "Taylor" in sent
    assert (await db_session.get(ActionItem, records[0][1])).status == ActionStatus.OPEN
    charge.side_effect = HTTPException(429, "Allowance reached")
    with pytest.raises(HTTPException) as error:
        await prepare_followup(
            records[0][0],
            FollowupRequest(channel="text", include_summary=True),
            Principal(user_id="followup_a"),
            db_session,
            settings,
        )
    assert error.value.status_code == 429
    assert provider.complete.await_count == 1


def test_empty_selection_rejected():
    with pytest.raises(HTTPException) as error:
        selected_facts(SimpleNamespace(action_items=[]), FollowupRequest(channel="email"))
    assert error.value.status_code == 422


@pytest.mark.parametrize("content", ["not json", '{"body":""}', '{"body":"   "}'])
async def test_invalid_provider_output_is_safe(content):
    provider = SimpleNamespace(complete=AsyncMock(return_value=AICompletionResult(content, "fake")))
    with pytest.raises(HTTPException) as error:
        await generate_draft(provider, "email", {})
    assert error.value.status_code == 502


async def test_provider_exception_does_not_expose_details():
    provider = SimpleNamespace(
        complete=AsyncMock(side_effect=RuntimeError("secret provider detail"))
    )
    with pytest.raises(HTTPException) as error:
        await generate_draft(provider, "email", {})
    assert "secret" not in error.value.detail


async def test_text_has_no_subject():
    provider = SimpleNamespace(
        complete=AsyncMock(
            return_value=AICompletionResult('{"subject":"Unexpected","body":"Next steps"}', "fake")
        )
    )
    assert (await generate_draft(provider, "text", {})).subject == ""
