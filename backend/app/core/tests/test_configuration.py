import os
import subprocess
import sys
import traceback

import pytest
from pydantic import ValidationError

from app.core.config import ConfigurationError, Settings, get_settings
from app.core.tests.test_production_config import production_settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_local_defaults_and_hosted_settings():
    assert Settings(_env_file=None).app_env == "development"
    for environment in ("staging", "production"):
        assert Settings(_env_file=None, **production_settings(app_env=environment)).auth_enabled


@pytest.mark.parametrize(
    "name",
    [
        "database_url",
        "redis_url",
        "openai_api_key",
        "anthropic_api_key",
        "s3_endpoint_url",
        "s3_region",
        "s3_bucket",
        "s3_access_key_id",
        "s3_secret_access_key",
        "clerk_secret_key",
    ],
)
def test_hosted_missing_required_values(name):
    values = production_settings()
    del values[name]
    with pytest.raises(ValidationError, match=name.upper()):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("database_url", "not-a-url"),
        ("database_url", "postgresql://user:password@db:99999/app"),
        ("database_url", "postgresql://db/app"),
        ("database_url", "postgresql://user:password@db"),
        ("redis_url", "https://redis:6379/0"),
        ("redis_url", "redis://redis/-1"),
        ("redis_url", "redis://redis/1?unsupported=value"),
        ("s3_endpoint_url", "https://user:secret@storage.test"),
        ("s3_endpoint_url", "https://storage.test:bad"),
        ("s3_bucket", "Invalid/Bucket"),
        ("openai_api_key", " leading-secret"),
        ("anthropic_api_key", "secret\n"),
        ("s3_secret_access_key", "embedded secret"),
        ("clerk_jwt_key", "not-a-public-key"),
        ("cors_origins", ("*",)),
        ("cors_origins", ("https://*",)),
        ("database_url", "postgresql://user:password@bad%host/app"),
        ("cors_origins", ("https://app.test/path",)),
        ("clerk_authorized_parties", ()),
        ("app_env", "prodution"),
        ("processing_mode", "unknown"),
        ("storage_backend", "unknown"),
        ("processing_max_tries", 0),
        ("processing_max_tries", 11),
        ("processing_job_timeout_seconds", 29),
        ("operations_queue_alert_threshold", 0),
        ("max_upload_size_bytes", 0),
        ("ai_request_timeout_seconds", 0),
        ("ai_request_timeout_seconds", float("nan")),
        ("ai_request_timeout_seconds", float("inf")),
        ("port", 65536),
        ("anthropic_model", ""),
        ("openai_whisper_model", " "),
        ("storage_root", ""),
        ("allowed_audio_mime_types", ()),
        ("allowed_audio_mime_types", ("invalid",)),
    ],
)
def test_malformed_values(name, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{name: value})


@pytest.mark.parametrize(
    "override",
    [
        {"clerk_authorized_parties": ("http://localhost:3000",)},
        {"cors_origins": ("https://127.0.0.1",)},
        {"s3_endpoint_url": "http://storage.test"},
        {"storage_backend": "local"},
    ],
)
def test_hosted_requirements(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **production_settings(**override))


def test_accepts_encoded_password_tls_redis_and_pem_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    pem = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:p%25%40ss@db/app",
        redis_url="rediss://user:password@redis:6380/2",
        auth_enabled=True,
        clerk_jwt_key=pem,
    )
    assert settings.database_url.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DATABASE_URL", "postgresql://user:SENTINEL_SECRET@db:invalid/app"),
        ("ANTHROPIC_API_KEY", "SENTINEL_SECRET\n"),
        ("AI_REQUEST_TIMEOUT_SECONDS", "SENTINEL_SECRET"),
        ("APP_ENV", "SENTINEL_SECRET"),
        ("CORS_ORIGINS", '["SENTINEL_SECRET"'),
    ],
)
def test_startup_errors_are_secret_safe(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    monkeypatch.setenv("OPENAI_API_KEY", "VALID_SECRET_SENTINEL")
    with pytest.raises(ConfigurationError) as caught:
        get_settings()
    output = "".join(traceback.format_exception(caught.value))
    assert name in output
    assert "SENTINEL_SECRET" not in output
    assert "VALID_SECRET_SENTINEL" not in output


@pytest.mark.parametrize(
    "command",
    [
        ["-c", "import app.main"],
        ["-c", "import app.processing.worker"],
        ["-m", "alembic", "upgrade", "head", "--sql"],
    ],
)
def test_real_entrypoints_fail_before_connecting_without_leaking_secrets(command):
    env = {**os.environ, "DATABASE_URL": "postgresql://u:STARTUP_SECRET@db:bad/app"}
    result = subprocess.run(
        [sys.executable, *command], env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr
    assert "STARTUP_SECRET" not in result.stdout + result.stderr
