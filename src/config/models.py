"""Pydantic models for configuration validation.

This module defines the data models for global and project-specific
configuration using Pydantic for validation and type safety.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application metadata configuration."""

    name: str = Field(default="PX BugHunter", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    description: str = Field(
        default="FastAPI application for receiving and processing Datadog bug report webhooks",
        description="Application description",
    )


class ServerConfig(BaseModel):
    """Server configuration settings."""

    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port", ge=1, le=65535)
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Debug mode")


class DatabaseConfig(BaseModel):
    """Database connection and pool configuration."""

    url: str = Field(
        default="postgresql://localhost:5432/px_bughunter",
        description="Database connection URL",
    )
    pool_size: int = Field(
        default=10,
        description="Number of connections to keep in the pool",
        ge=1,
    )
    max_overflow: int = Field(
        default=20,
        description="Maximum number of connections that can be created beyond pool_size",
        ge=0,
    )
    pool_timeout: int = Field(
        default=30,
        description="Seconds to wait before giving up on getting a connection from the pool",
        ge=1,
    )
    pool_recycle: int = Field(
        default=3600,
        description="Seconds after which a connection is automatically recycled",
        ge=-1,
    )
    echo: bool = Field(
        default=False,
        description="Log all SQL statements (useful for debugging)",
    )


class LLMConfig(BaseModel):
    """Large Language Model configuration."""

    provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, etc.)",
    )
    model: str = Field(
        default="gpt-4",
        description="Model name to use",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for the LLM provider",
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0 to 1.0)",
        ge=0.0,
        le=2.0,
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum number of tokens to generate",
        ge=1,
    )
    timeout: int = Field(
        default=60,
        description="Request timeout in seconds",
        ge=1,
    )


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    format: str = Field(
        default="json",
        description="Output format (json, yaml, text)",
    )
    directory: str = Field(
        default="./output",
        description="Directory for output files",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in output",
    )
    pretty_print: bool = Field(
        default=True,
        description="Pretty-print output for readability",
    )


class CORSConfig(BaseModel):
    """CORS (Cross-Origin Resource Sharing) configuration."""

    origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )
    allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods",
    )
    allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed HTTP headers",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file: Optional[str] = Field(
        default=None,
        description="Optional log file path",
    )


class GlobalConfig(BaseModel):
    """Global configuration for the entire application.

    This model represents the structure of config/global.yaml and includes
    all system-wide settings for the application.
    """

    app: AppConfig = Field(
        default_factory=AppConfig,
        description="Application metadata",
    )
    server: ServerConfig = Field(
        default_factory=ServerConfig,
        description="Server configuration",
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration",
    )
    llm: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration",
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration",
    )
    cors: CORSConfig = Field(
        default_factory=CORSConfig,
        description="CORS configuration",
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
