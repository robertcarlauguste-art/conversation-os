import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides) -> dict:
    values = {
        "app_env": "production",
        "auth_enabled": True,
        "clerk_secret_key": "sk_test_example",
        "database_url": "postgresql://user:password@db:5432/app",
        "redis_url": "redis://redis:6379/0",
        "openai_api_key": "test-openai",
        "anthropic_api_key": "test-anthropic",
        "storage_backend": "s3",
        "s3_endpoint_url": "https://example.r2.cloudflarestorage.com",
        "s3_region": "auto",
        "s3_bucket": "test-bucket",
        "s3_access_key_id": "test-access",
        "s3_secret_access_key": "test-secret",
        "clerk_authorized_parties": ("https://app.example.com",),
        "processing_mode": "queue",
        "cors_origins": ("https://app.example.com",),
    }
    values.update(overrides)
    return values


def test_production_configuration_accepts_secure_runtime() -> None:
    settings = Settings(**production_settings())
    assert settings.processing_mode == "queue"


def test_railway_postgres_url_uses_async_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@postgres:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:password@postgres:5432/app"


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
