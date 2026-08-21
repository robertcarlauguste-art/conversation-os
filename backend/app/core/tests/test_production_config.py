import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides) -> dict:
    values = {
        "app_env": "production",
        "auth_enabled": True,
        "clerk_jwt_key": "test-public-key",
        "processing_mode": "queue",
        "cors_origins": ("https://app.example.com",),
    }
    values.update(overrides)
    return values


def test_production_configuration_accepts_secure_runtime() -> None:
    settings = Settings(**production_settings())
    assert settings.processing_mode == "queue"


@pytest.mark.parametrize(
    "override",
    [
        {"auth_enabled": False, "clerk_jwt_key": None},
        {"processing_mode": "inline"},
        {"cors_origins": ("http://localhost:3000",)},
    ],
)
def test_production_configuration_fails_closed(override) -> None:
    with pytest.raises(ValidationError):
        Settings(**production_settings(**override))
