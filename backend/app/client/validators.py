"""
Business validation for client facts, mirroring memory/validators.py's
pattern: cap sizes so a malformed upstream extraction can't create
unbounded rows, and reject blank entries.
"""

MAX_FACT_LENGTH = 1000


class ClientValidationError(Exception):
    """Raised when a fact fails a business rule. Message is log-facing."""


def validate_fact_text(fact_text: str) -> None:
    if not fact_text.strip():
        raise ClientValidationError("Fact text cannot be blank or whitespace-only.")
    if len(fact_text) > MAX_FACT_LENGTH:
        raise ClientValidationError(
            f"Fact text is {len(fact_text)} characters, "
            f"which exceeds the {MAX_FACT_LENGTH} character limit."
        )
