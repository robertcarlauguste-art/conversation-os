"""Opt-in real-provider regressions. Uses fictional text, never writes application data.

Run with RUN_LIVE_ACCURACY=1 and configured provider credentials. These checks cost
provider usage and assess a small sample, not a general accuracy percentage.
"""

import json
import os
from pathlib import Path

import pytest

from app.client.completion_review import assess_completions
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


@pytest.mark.parametrize(
    "case",
    json.loads((Path(__file__).with_name("completion_cases.json")).read_text()),
    ids=lambda case: case["name"],
)
async def test_focused_completion_cases(case):
    settings = get_settings()
    provider = ClaudeProvider(settings.anthropic_api_key, settings.anthropic_model)
    source = "00000000-0000-4000-8000-000000000001"
    later = "00000000-0000-4000-8000-000000000002"
    action = "00000000-0000-4000-8000-000000000003"
    payload = {
        "client": "Morgan Vale",
        "sources": [
            {
                "id": source,
                "uploaded_at": "2026-09-23T10:00:00+00:00",
                "text": "I will send two listings to Morgan Vale.",
            },
            {"id": later, "uploaded_at": "2026-09-24T10:00:00+00:00", "text": case["text"]},
        ],
        "open_actions": [
            {
                "id": action,
                "task": "Send two listings to Morgan Vale",
                "owner": None,
                "source_conversation_id": source,
            }
        ],
    }
    result = await assess_completions(provider, payload)
    assert bool(result) is case["expected"]
