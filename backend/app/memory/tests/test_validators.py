from typing import Any

import pytest

from app.memory.schemas import ExtractionResult
from app.memory.validators import MemoryValidationError, validate_extraction


def _extraction(**overrides: Any) -> ExtractionResult:
    defaults: dict[str, Any] = dict(
        summary="A short summary.",
        decisions=["Decision A"],
        action_items=[{"task": "Do the thing"}],
        people=[{"name": "Jane Doe"}],
        topics=["financing"],
        confidence=0.8,
    )
    defaults.update(overrides)
    return ExtractionResult(**defaults)


def test_accepts_valid_extraction() -> None:
    validate_extraction(_extraction())


def test_rejects_blank_summary() -> None:
    with pytest.raises(MemoryValidationError, match="blank"):
        validate_extraction(_extraction(summary="   "))


def test_rejects_oversized_summary() -> None:
    with pytest.raises(MemoryValidationError, match="exceeds"):
        validate_extraction(_extraction(summary="x" * 5001))


def test_rejects_too_many_action_items() -> None:
    with pytest.raises(MemoryValidationError, match="action_items"):
        validate_extraction(
            _extraction(
                action_items=[{"task": f"item {i}"} for i in range(51)]
            )
        )


def test_rejects_blank_entry_in_list() -> None:
    with pytest.raises(MemoryValidationError, match="blank entry"):
        validate_extraction(
            _extraction(people=[{"name": "Jane Doe"}, {"name": "   "}])
        )


def test_confidence_out_of_range_rejected_by_schema() -> None:
    with pytest.raises(ValueError):
        _extraction(confidence=1.5)
