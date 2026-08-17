"""
Validation rules for extracted memory data.

Runs after:
Conversation → LLM → JSON → Pydantic

and before:
Persistence → Database
"""

from app.memory.schemas import ExtractionResult


class MemoryValidationError(Exception):
    """
    Raised when extracted memory data fails validation.
    """


def _validate_string_list(
    field_name: str,
    values: list[str],
) -> None:

    if any(
        not value.strip()
        for value in values
    ):
        raise MemoryValidationError(
            f"{field_name} contains empty values"
        )


def validate_extraction(
    extraction: ExtractionResult,
) -> None:
    """
    Validate extracted conversation memory.
    """

    if not extraction.summary.strip():

        raise MemoryValidationError(
            "Summary cannot be empty"
        )


    if not 0 <= extraction.confidence <= 1:

        raise MemoryValidationError(
            "Confidence must be between 0 and 1"
        )


    # Decisions remain simple strings
    _validate_string_list(
        "decisions",
        extraction.decisions,
    )


    # Topics remain simple strings
    _validate_string_list(
        "topics",
        extraction.topics,
    )


    # Rich action items
    for item in extraction.action_items:

        if not item.task.strip():

            raise MemoryValidationError(
                "Action item task cannot be empty"
            )


    # Rich people objects
    for person in extraction.people:

        if not person.name.strip():

            raise MemoryValidationError(
                "Person name cannot be empty"
            )