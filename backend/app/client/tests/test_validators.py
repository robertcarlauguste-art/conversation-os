import pytest

from app.client.validators import ClientValidationError, validate_fact_text


def test_accepts_valid_fact() -> None:
    validate_fact_text("Prefers 3-bedroom homes")


def test_rejects_blank_fact() -> None:
    with pytest.raises(ClientValidationError, match="blank"):
        validate_fact_text("   ")


def test_rejects_oversized_fact() -> None:
    with pytest.raises(ClientValidationError, match="exceeds"):
        validate_fact_text("x" * 1001)
