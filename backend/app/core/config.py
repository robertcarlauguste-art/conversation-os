"""
Centralized application configuration.

Rule 4 (ADR-002): all environment-driven configuration must live here.
Nothing else in the codebase should call os.environ directly — think of
this file as the single circuit-breaker panel for the whole app. Every
"room" (module) draws power (config) from here instead of wiring its
own connection to the street.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = Field(default="ConversationOS")
    app_env: str = Field(default="development")
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
    max_upload_size_bytes: int = Field(default=100 * 1024 * 1024)  # 100 MB
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
    ai_request_timeout_seconds: float = Field(default=60.0)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        if self.storage_backend == "s3":
            required_storage_settings = {
                "S3_ENDPOINT_URL": self.s3_endpoint_url,
                "S3_REGION": self.s3_region,
                "S3_BUCKET": self.s3_bucket,
                "S3_ACCESS_KEY_ID": self.s3_access_key_id,
                "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
            }
            missing = [name for name, value in required_storage_settings.items() if not value]
            if missing:
                raise ValueError("STORAGE_BACKEND=s3 requires " + ", ".join(sorted(missing)))
        if self.auth_enabled and not (self.clerk_secret_key or self.clerk_jwt_key):
            raise ValueError("AUTH_ENABLED requires CLERK_SECRET_KEY or CLERK_JWT_KEY")
        if self.app_env == "production":
            if not self.auth_enabled:
                raise ValueError("Production requires AUTH_ENABLED=true")
            if self.processing_mode != "queue":
                raise ValueError("Production requires PROCESSING_MODE=queue")
            if any("localhost" in origin for origin in self.cors_origins):
                raise ValueError("Production CORS_ORIGINS cannot contain localhost")
        return self


@lru_cache
def get_settings() -> Settings:
    """Settings is cached so every module shares one instance (one panel, not one per room)."""
    return Settings()
