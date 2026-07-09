"""
Centralized application configuration.

Rule 4 (ADR-002): all environment-driven configuration must live here.
Nothing else in the codebase should call os.environ directly — think of
this file as the single circuit-breaker panel for the whole app. Every
"room" (module) draws power (config) from here instead of wiring its
own connection to the street.
"""

from functools import lru_cache

from pydantic import Field
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

    # AI providers (keys only — no client instantiation here; see app/providers)
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Supabase (scaffold only, per Sprint 0 scope)
    supabase_url: str | None = Field(default=None)
    supabase_key: str | None = Field(default=None)

    # Auth (scaffold only, per Sprint 0 scope)
    clerk_secret_key: str | None = Field(default=None)

    # Storage (Sprint 1 — conversation intake)
    storage_root: str = Field(default="/app/storage/uploads")
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


@lru_cache
def get_settings() -> Settings:
    """Settings is cached so every module shares one instance (one panel, not one per room)."""
    return Settings()
