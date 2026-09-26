import uuid

import pytest

from app.client.review import ReviewDraft, validate_sources


def test_review_rejects_invented_quotes_and_foreign_sources():
    source = str(uuid.uuid4())
    draft = ReviewDraft.model_validate(
        {
            "details": [
                {
                    "label": "Budget",
                    "value": "$375,000",
                    "source_conversation_id": source,
                    "quote": "I never said this",
                }
            ]
        }
    )
    with pytest.raises(ValueError):
        validate_sources(draft, {source: "Budget is $375,000"}, {})
    draft.details[0].quote = "Budget is $375,000"
    validate_sources(draft, {source: "Budget is $375,000"}, {})
    with pytest.raises(ValueError):
        validate_sources(draft, {}, {})
