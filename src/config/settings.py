"""Application settings management using Pydantic BaseSettings."""

from functools import cached_property
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

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

    @cached_property
    def cors_origins(self) -> List[str]:
        return parse_comma_list(self.cors_origins_str)

    @cached_property
    def cors_allow_methods(self) -> List[str]:
        return parse_comma_list(self.cors_allow_methods_str)

    @cached_property
    def cors_allow_headers(self) -> List[str]:
        return parse_comma_list(self.cors_allow_headers_str)


# Global settings instance
settings = Settings()
