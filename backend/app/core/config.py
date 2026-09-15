"""
Centralized application configuration.

Rule 4 (ADR-002): all environment-driven configuration must live here.
Nothing else in the codebase should call os.environ directly — think of
this file as the single circuit-breaker panel for the whole app. Every
"room" (module) draws power (config) from here instead of wiring its
own connection to the street.
"""

import re
from functools import lru_cache
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.exceptions import SettingsError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # App
    app_name: str = Field(default="ConversationOS")
    app_env: Literal["development", "test", "staging", "production"] = "development"
    port: int = Field(default=8000, ge=1, le=65535)
    version: str = Field(default="0.1.0")

    # Data stores
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/conversation_os"
    )
    redis_url: str = Field(default="redis://redis:6379/0")
    processing_mode: str = Field(default="inline", pattern="^(inline|queue)$")
    processing_max_tries: int = Field(default=3, ge=1, le=10)
    processing_job_timeout_seconds: int = Field(default=300, ge=30)
    operations_queue_alert_threshold: int = Field(default=25, ge=1)
    # Operator-only monitoring process; never consumed by tenant HTTP routes.
    monitoring_api_url: str | None = None
    monitoring_webhook_url: str | None = Field(default=None, repr=False)
    monitoring_heartbeat_url: str | None = Field(default=None, repr=False)
    monitoring_alert_heartbeat_url: str | None = Field(default=None, repr=False)
    monitoring_state_path: str = "/data/monitoring-state.json"
    monitoring_interval_seconds: int = Field(default=60, ge=30)
    monitoring_consecutive_checks: int = Field(default=2, ge=1)
    monitoring_failure_window_seconds: int = Field(default=900, ge=60)
    monitoring_provider_failure_threshold: int = Field(default=3, ge=1)

    @field_validator(
        "monitoring_api_url",
        "monitoring_webhook_url",
        "monitoring_heartbeat_url",
        "monitoring_alert_heartbeat_url",
    )
    @classmethod
    def validate_monitoring_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.fragment
            ):
                raise ValueError("provide an HTTPS URL without user info or fragment")
            try:
                _ = parsed.port
            except ValueError:
                raise ValueError("provide a valid HTTPS port") from None
        return value

    @model_validator(mode="after")
    def validate_monitoring_delivery(self):
        if self.monitoring_alert_heartbeat_url:
            if self.monitoring_webhook_url:
                raise ValueError("choose webhook or alert heartbeat delivery, not both")
            if urlsplit(self.monitoring_alert_heartbeat_url).query:
                raise ValueError("alert heartbeat URL must not contain query parameters")
            if self.monitoring_alert_heartbeat_url.rstrip("/") == (
                self.monitoring_heartbeat_url or ""
            ).rstrip("/"):
                raise ValueError("operational health and process heartbeats must be distinct")
        return self

    cors_origins: tuple[str, ...] = Field(
        default=("http://localhost:3000", "http://localhost:3001")
    )

    # AI providers (keys only — no client instantiation here; see app/providers)
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Supabase (scaffold only, per Sprint 0 scope)
    supabase_url: str | None = Field(default=None)
    supabase_key: str | None = Field(default=None)

    # Auth (Sprint 5 - Clerk identity boundary)
    auth_enabled: bool = Field(default=False)
    auth_dev_user_id: str = Field(default="dev_user")
    clerk_secret_key: str | None = Field(default=None)
    clerk_jwt_key: str | None = Field(default=None)
    clerk_authorized_parties: tuple[str, ...] = Field(
        default=("http://localhost:3000", "http://localhost:3001")
    )

    # Storage (Sprint 1 — conversation intake)
    storage_backend: str = Field(default="local", pattern="^(local|s3)$")
    storage_root: str = Field(default="/app/storage/uploads")
    s3_endpoint_url: str | None = Field(default=None)
    s3_region: str | None = Field(default=None)
    s3_bucket: str | None = Field(default=None)
    s3_access_key_id: str | None = Field(default=None)
    s3_secret_access_key: str | None = Field(default=None)
    max_upload_size_bytes: int = Field(default=100 * 1024 * 1024, ge=1)  # 100 MB
    allowed_audio_mime_types: tuple[str, ...] = Field(
        default=(
            "audio/mpeg",  # mp3
            "audio/wav",
            "audio/x-wav",
            "audio/m4a",
            "audio/x-m4a",
            "audio/mp4",  # m4a is often reported as audio/mp4
            "audio/aac",
        )
    )

    # AI pipeline (Sprint 2 — memory & intelligence)
    anthropic_model: str = Field(default="claude-sonnet-5")
    openai_whisper_model: str = Field(default="whisper-1")
    ai_request_timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)

    @field_validator("*", mode="before")
    @classmethod
    def reject_unsafe_text(cls, value: object, info) -> object:
        # Do not silently trim credentials: that hides deployment mistakes.
        if isinstance(value, str):
            if value != value.strip() or any(ord(c) < 32 for c in value):
                if info.field_name != "clerk_jwt_key":
                    raise ValueError("remove surrounding whitespace and control characters")
            if not value:
                if cls.model_fields[info.field_name].default is None:
                    return None
                raise ValueError("must not be empty")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
        validate_url(value, {"postgresql+psycopg", "postgresql+asyncpg"}, credentials=True)
        parsed = urlsplit(value)
        if not parsed.username or not parsed.password or not parsed.path.strip("/"):
            raise ValueError("requires a PostgreSQL username, password, host and database")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        validate_url(value, {"redis", "rediss"}, credentials=True)
        parsed = urlsplit(value)
        if parsed.path not in ("", "/") and not re.fullmatch(r"/[0-9]+", parsed.path):
            raise ValueError("database index must be a nonnegative integer")
        if parsed.query:
            raise ValueError("query parameters are unsupported by the queue client")
        return value

    @field_validator("s3_endpoint_url", "supabase_url")
    @classmethod
    def validate_http_url(cls, value: str | None) -> str | None:
        if value:
            validate_url(value, {"http", "https"})
        return value

    @field_validator("cors_origins", "clerk_authorized_parties")
    @classmethod
    def validate_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("provide a nonempty JSON array of exact HTTP(S) origins")
        for value in values:
            validate_url(value, {"http", "https"})
            if urlsplit(value).path:
                raise ValueError("origins must not include a path or trailing slash")
        return values

    @field_validator("s3_bucket")
    @classmethod
    def validate_bucket(cls, value: str | None) -> str | None:
        if value and (
            not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value)
            or ".." in value
            or re.fullmatch(r"[0-9.]+", value)
        ):
            raise ValueError("use a 3-63 character lowercase S3 bucket name")
        return value

    @field_validator(
        "openai_api_key",
        "anthropic_api_key",
        "clerk_secret_key",
        "s3_access_key_id",
        "s3_secret_access_key",
        "supabase_key",
        "anthropic_model",
        "openai_whisper_model",
        "s3_region",
    )
    @classmethod
    def validate_token(cls, value: str | None) -> str | None:
        if value and any(c.isspace() for c in value):
            raise ValueError("must not contain whitespace")
        return value

    @field_validator("clerk_jwt_key")
    @classmethod
    def validate_jwt_key(cls, value: str | None) -> str | None:
        if value:
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            try:
                key = load_pem_public_key(value.encode())
                if not isinstance(key, RSAPublicKey):
                    raise ValueError()
            except Exception:
                raise ValueError("provide an RSA public key in PEM format") from None
        return value

    @field_validator("allowed_audio_mime_types")
    @classmethod
    def validate_mime_types(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not re.fullmatch(r"audio/[A-Za-z0-9.+-]+", v) for v in values):
            raise ValueError("provide a nonempty JSON array of audio MIME types")
        return values

    @model_validator(mode="after")
    def validate_required_configuration(self) -> "Settings":
        problems = []
        if self.storage_backend == "s3":
            for name in (
                "s3_endpoint_url",
                "s3_region",
                "s3_bucket",
                "s3_access_key_id",
                "s3_secret_access_key",
            ):
                if not getattr(self, name):
                    problems.append(f"{name.upper()}: required when STORAGE_BACKEND=s3")
        if self.auth_enabled and not (self.clerk_secret_key or self.clerk_jwt_key):
            problems.append("AUTH_ENABLED: requires CLERK_SECRET_KEY or CLERK_JWT_KEY")
        if self.app_env in {"staging", "production"}:
            for name in ("database_url", "redis_url", "openai_api_key", "anthropic_api_key"):
                if name not in self.model_fields_set or not getattr(self, name):
                    problems.append(f"{name.upper()}: set explicitly for hosted environments")
            if not self.auth_enabled:
                problems.append("AUTH_ENABLED: hosted environments require true")
            if self.processing_mode != "queue":
                problems.append("PROCESSING_MODE: hosted environments require queue")
            if self.storage_backend != "s3":
                problems.append("STORAGE_BACKEND: hosted API and worker require shared s3 storage")
            for name in ("cors_origins", "clerk_authorized_parties"):
                for origin in getattr(self, name):
                    parsed = urlsplit(origin)
                    if parsed.scheme != "https" or is_loopback_host(parsed.hostname or ""):
                        problems.append(f"{name.upper()}: use exact public HTTPS origins")
                        break
            if self.s3_endpoint_url and urlsplit(self.s3_endpoint_url).scheme != "https":
                problems.append("S3_ENDPOINT_URL: hosted storage requires HTTPS")
        if problems:
            raise ValueError("; ".join(problems))
        return self


def valid_host(host: str) -> bool:
    try:
        ip_address(host)
        return True
    except ValueError:
        return (
            bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?", host))
            and ".." not in host
        )


def is_loopback_host(host: str) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def validate_url(value: str, schemes: set[str], *, credentials: bool = False) -> None:
    # Parser errors sometimes embed their input. Never forward them.
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in schemes
            and valid_host(parsed.hostname or "")
            and not parsed.fragment
            and not any(c.isspace() for c in value)
            and "\\" not in value
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
        if not credentials:
            valid = valid and not parsed.username and not parsed.password and not parsed.query
        if not valid:
            raise ValueError()
    except ValueError:
        raise ValueError(
            "provide a valid " + "/".join(sorted(schemes)) + " URL with host and valid port"
        ) from None


class ConfigurationError(RuntimeError):
    """Safe to emit in startup logs; contains no configuration values."""


@lru_cache
def get_settings() -> Settings:
    """All process entry points load this before constructing clients or serving traffic."""
    try:
        return Settings()
    except ValidationError as exc:
        details = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            name = ".".join(str(part).upper() for part in error["loc"]) or "CONFIGURATION"
            # Our validators use static messages; Pydantic messages do not include inputs.
            details.append(f"{name}: {error['msg']}")
        raise ConfigurationError("Invalid configuration:\n- " + "\n- ".join(details)) from None
    except SettingsError:
        # JSON decoding occurs before model validation. Do not expose the exception chain.
        raise ConfigurationError(
            "Invalid configuration: check JSON arrays in CORS_ORIGINS, "
            "CLERK_AUTHORIZED_PARTIES and ALLOWED_AUDIO_MIME_TYPES."
        ) from None
