"""
Business-level validation for extraction results, beyond what
`ExtractionResult`'s Pydantic types already check (which only
constrain shape/type, not domain-reasonable content).
"""

from app.memory.schemas import ExtractionResult

MAX_SUMMARY_LENGTH = 5000
MAX_LIST_ITEMS = 50


class MemoryValidationError(Exception):
    """Raised when an extraction result fails a business rule. Message is user/log-facing."""


def validate_extraction(extraction: ExtractionResult) -> None:
    if not extraction.summary.strip():
        raise MemoryValidationError("Summary cannot be blank or whitespace-only.")

    if len(extraction.summary) > MAX_SUMMARY_LENGTH:
        raise MemoryValidationError(
            f"Summary is {len(extraction.summary)} characters, "
            f"which exceeds the {MAX_SUMMARY_LENGTH} character limit."
        )

    for field_name, values in (
        ("decisions", extraction.decisions),
        ("action_items", extraction.action_items),
        ("people", extraction.people),
        ("topics", extraction.topics),
    ):
        if len(values) > MAX_LIST_ITEMS:
            raise MemoryValidationError(
                f"'{field_name}' has {len(values)} items, "
                f"which exceeds the {MAX_LIST_ITEMS} item limit."
            )
        if any(not item.strip() for item in values):
            raise MemoryValidationError(f"'{field_name}' contains a blank entry.")
