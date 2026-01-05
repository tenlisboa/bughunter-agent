"""Application settings management using Pydantic BaseSettings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # CORS configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed HTTP methods for CORS")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed headers for CORS")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")


# Global settings instance
settings = Settings()
