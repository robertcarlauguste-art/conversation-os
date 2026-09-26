import uuid

import pytest

from app.client.completion_review import CompletionDraft, validate_assessments


def fixture():
    action, origin, later = (str(uuid.uuid4()) for _ in range(3))
    payload = {
        "open_actions": [{"id": action, "source_conversation_id": origin}],
        "sources": [
            {
                "id": origin,
                "uploaded_at": "2026-09-23T10:00:00+00:00",
                "text": "I will send two listings.",
            },
            {
                "id": later,
                "uploaded_at": "2026-09-24T10:00:00+00:00",
                "text": "I sent the two listings.",
            },
        ],
    }
    response = {
        "assessments": [
            {
                "action_id": action,
                "outcome": "completed",
                "source_conversation_id": later,
                "quote": "I sent the two listings.",
            }
        ]
    }
    return payload, response


def test_completion_requires_exact_quote_and_later_owned_source():
    payload, response = fixture()
    assert len(validate_assessments(CompletionDraft.model_validate(response), payload)) == 1
    for change in (
        {"quote": "invented"},
        {"source_conversation_id": str(uuid.uuid4())},
        {
            "source_conversation_id": payload["sources"][0]["id"],
            "quote": "I will send two listings.",
        },
    ):
        amended = {"assessments": [response["assessments"][0] | change]}
        with pytest.raises(ValueError):
            validate_assessments(CompletionDraft.model_validate(amended), payload)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "foreign"])
def test_every_task_must_be_assessed_exactly_once(kind):
    payload, response = fixture()
    if kind == "missing":
        response["assessments"] = []
    elif kind == "duplicate":
        response["assessments"] *= 2
    else:
        response["assessments"][0]["action_id"] = str(uuid.uuid4())
    with pytest.raises(ValueError):
        validate_assessments(CompletionDraft.model_validate(response), payload)


@pytest.mark.parametrize("outcome", ["not_completed", "uncertain"])
def test_unfinished_or_uncertain_assessment_never_produces_suggestion(outcome):
    payload, response = fixture()
    response["assessments"][0].update(outcome=outcome, quote=None, source_conversation_id=None)
    assert validate_assessments(CompletionDraft.model_validate(response), payload) == []
