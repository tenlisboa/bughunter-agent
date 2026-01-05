"""Application settings management using Pydantic BaseSettings."""

import logging
from functools import cached_property
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def parse_comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables and YAML.

    This class supports loading configuration from multiple sources with the following priority:
    1. Environment variables (highest priority)
    2. YAML configuration file (config/global.yaml)
    3. Default values (lowest priority)

    The YAML configuration file is optional - if it doesn't exist, the class falls back
    to environment variables and defaults, maintaining backward compatibility.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="PX BugHunter", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    app_description: str = Field(
        default="FastAPI application for receiving and processing Datadog bug report webhooks",
        description="Application description",
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port", ge=1, le=65535)

    # Environment and debug settings
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")

    # CORS configuration (stored as comma-separated strings)
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="cors_origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_allow_methods_str: str = Field(default="*", alias="cors_allow_methods")
    cors_allow_headers_str: str = Field(default="*", alias="cors_allow_headers")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Settings with values from YAML config and environment variables.

        Environment variables take precedence over YAML values, which take precedence
        over default values. If the YAML config file doesn't exist, only environment
        variables and defaults are used (backward compatible behavior).
        """
        # Try to load from YAML config if available
        yaml_values = self._load_from_yaml()

        # Merge YAML values with any provided kwargs (kwargs take precedence)
        if yaml_values:
            # Only use YAML values that weren't explicitly provided
            for key, value in yaml_values.items():
                if key not in kwargs:
                    kwargs[key] = value

        # Call parent __init__ which will apply environment variables on top
        # (environment variables take highest precedence)
        super().__init__(**kwargs)

    @staticmethod
    def _load_from_yaml() -> dict[str, Any] | None:
        """Load configuration values from YAML file.

        Returns:
            Dictionary of configuration values from YAML, or None if not available.
        """
        try:
            # Import here to avoid circular imports and to keep it optional
            from src.config.yaml_loader import load_global_config

            # Try to load global config
            global_config = load_global_config()

            # Map GlobalConfig fields to Settings fields
            yaml_values = {
                "app_name": global_config.app.name,
                "app_version": global_config.app.version,
                "app_description": global_config.app.description,
                "host": global_config.server.host,
                "port": global_config.server.port,
                "environment": global_config.server.environment,
                "debug": global_config.server.debug,
                "cors_origins_str": ",".join(global_config.cors.origins),
                "cors_allow_credentials": global_config.cors.allow_credentials,
                "cors_allow_methods_str": ",".join(global_config.cors.allow_methods),
                "cors_allow_headers_str": ",".join(global_config.cors.allow_headers),
                "log_level": global_config.logging.level,
            }

            logger.info("Successfully loaded configuration from YAML")
            return yaml_values

        except FileNotFoundError:
            # YAML config file doesn't exist - this is OK for backward compatibility
            logger.debug("YAML config file not found, using environment variables and defaults")
            return None
        except Exception as e:
            # Log the error but don't fail - fall back to env vars and defaults
            logger.warning(f"Failed to load YAML config: {e}. Using environment variables and defaults.")
            return None

    @cached_property
    def cors_origins(self) -> list[str]:
        return parse_comma_list(self.cors_origins_str)

    @cached_property
    def cors_allow_methods(self) -> list[str]:
        return parse_comma_list(self.cors_allow_methods_str)

    @cached_property
    def cors_allow_headers(self) -> list[str]:
        return parse_comma_list(self.cors_allow_headers_str)


# Global settings instance
settings = Settings()
