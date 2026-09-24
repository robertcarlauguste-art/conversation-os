"""Opt-in real-provider regressions. Uses fictional text, never writes application data.

Run with RUN_LIVE_ACCURACY=1 and configured provider credentials. These checks cost
provider usage and assess a small sample, not a general accuracy percentage.
"""

import os

import pytest

from app.client.review import PROMPT, ReviewDraft, validate_sources
from app.core.config import get_settings
from app.memory.schemas import ExtractionResult
from app.memory.service import EXTRACTION_SYSTEM_PROMPT
from app.providers.ai_provider import AIMessage
from app.providers.claude_provider import ClaudeProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_ACCURACY") != "1", reason="Explicit live-provider opt-in required"
)


async def complete(prompt, text):
    settings = get_settings()
    provider = ClaudeProvider(settings.anthropic_api_key, settings.anthropic_model)
    result = await provider.complete([AIMessage(role="user", content=text)], system=prompt)
    return result.content


@pytest.mark.parametrize(
    "transcript",
    [
        "Casey Reed might call a lender, but has not decided. No next steps were agreed.",
        "Taylor Quinn and I may meet next week, but no date is agreed.",
        "Morgan Vale earlier said $340,000. Today they mentioned $300,000, "
        "but I am not sure whether that is their new budget.",
    ],
)
async def test_uncertainty_does_not_create_commitments(transcript):
    draft = ExtractionResult.model_validate_json(
        await complete(EXTRACTION_SYSTEM_PROMPT, transcript)
    )
    assert draft.action_items == []
    assert draft.decisions == []


async def test_explicit_completion_with_unnamed_speaker():
    import json

    source = "00000000-0000-4000-8000-000000000001"
    send = "00000000-0000-4000-8000-000000000002"
    call = "00000000-0000-4000-8000-000000000003"
    text = "I sent the two listings. Morgan Vale has not called the lender yet."
    payload = {
        "client": "Morgan Vale",
        "sources": [{"id": source, "text": text}],
        "open_actions": [
            {"id": send, "task": "Send two listings to Morgan Vale", "owner": None},
            {"id": call, "task": "Call the lender", "owner": "Morgan Vale"},
        ],
    }
    draft = ReviewDraft.model_validate_json(await complete(PROMPT, json.dumps(payload)))
    validate_sources(draft, {source: text}, {send: "Send listings", call: "Call lender"})
    assert {str(item.action_id) for item in draft.completed_actions} == {send}
