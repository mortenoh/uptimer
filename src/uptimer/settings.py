"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="UPTIMER_",
        case_sensitive=False,
    )

    # Auth
    username: str = "admin"
    password: str = "admin"
    secret_key: str = "change-me-in-production"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
