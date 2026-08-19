"""
Validation rules for extracted memory data.

Runs after:
Conversation → LLM → JSON → Pydantic

and before:
Persistence → Database
"""

from app.memory.schemas import ExtractionResult

MAX_SUMMARY_LENGTH = 5000
MAX_ACTION_ITEMS = 50


class MemoryValidationError(Exception):
    """
    Raised when extracted memory data fails validation.
    """


def _validate_string_list(
    field_name: str,
    values: list[str],
) -> None:

    if any(not value.strip() for value in values):
        raise MemoryValidationError(f"{field_name} contains empty values")


def validate_extraction(
    extraction: ExtractionResult,
) -> None:
    """
    Validate extracted conversation memory.
    """

    if not extraction.summary.strip():

        raise MemoryValidationError("Summary cannot be blank")

    if len(extraction.summary) > MAX_SUMMARY_LENGTH:

        raise MemoryValidationError(f"Summary exceeds {MAX_SUMMARY_LENGTH} characters")

    if not 0 <= extraction.confidence <= 1:

        raise MemoryValidationError("Confidence must be between 0 and 1")

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

    if len(extraction.action_items) > MAX_ACTION_ITEMS:

        raise MemoryValidationError(f"action_items exceeds maximum of {MAX_ACTION_ITEMS}")

    # Rich action items
    for item in extraction.action_items:

        if not item.task.strip():

            raise MemoryValidationError("action_items contains blank entry")

    # Rich people objects
    for person in extraction.people:

        if not person.name.strip():

            raise MemoryValidationError("people contains blank entry")
