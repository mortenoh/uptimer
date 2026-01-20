"""Application settings with YAML + dotenv support."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class MonitorConfig(BaseModel):
    """Configuration for a single monitor."""

    url: str
    checker: str = "http"
    username: str | None = None
    password: str | None = None
    interval: int = 60  # seconds


class Settings(BaseSettings):
    """Application settings loaded from YAML, env, and dotenv."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="UPTIMER_",
        case_sensitive=False,
        extra="ignore",
    )

    # Auth
    username: str = "admin"
    password: str = "admin"
    secret_key: str = "change-me-in-production"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Storage (MongoDB)
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "uptimer"
    results_retention: int = 10_000_000  # Max results per monitor

    # Monitors (from YAML)
    monitors: list[MonitorConfig] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to include YAML."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
            file_secret_settings,
        )


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Load settings from config.yaml file."""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """Get field value from YAML config."""
        yaml_data = self._load_yaml()
        if field_name in yaml_data:
            return yaml_data[field_name], field_name, False
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return all settings from YAML."""
        return self._load_yaml()

    def _load_yaml(self) -> dict[str, Any]:
        """Load and parse YAML config file."""
        config_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path.home() / ".config" / "uptimer" / "config.yaml",
        ]

        for path in config_paths:
            if path.exists():
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                    return data

        return {}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
