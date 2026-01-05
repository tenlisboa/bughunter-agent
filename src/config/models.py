"""Pydantic models for configuration validation.

This module defines the data models for global and project-specific
configuration using Pydantic for validation and type safety.
"""


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
    api_key: str | None = Field(
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

    origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )
    allow_methods: list[str] = Field(
        default=["*"],
        description="Allowed HTTP methods",
    )
    allow_headers: list[str] = Field(
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
    file: str | None = Field(
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


# ============================================================================
# Project Configuration Models
# ============================================================================


class RepositoryConfig(BaseModel):
    """Repository configuration for project."""

    url: str = Field(
        description="Git repository URL (HTTPS or SSH)",
    )
    branch: str = Field(
        default="main",
        description="Default branch to clone/checkout",
    )
    clone_path: str = Field(
        description="Local path where repository should be cloned",
    )
    ssh_key: str | None = Field(
        default=None,
        description="Optional SSH key path for authentication",
    )
    username: str | None = Field(
        default=None,
        description="Optional username for HTTPS authentication",
    )
    password: str | None = Field(
        default=None,
        description="Optional password/token for HTTPS authentication",
    )


class IndexingConfig(BaseModel):
    """Indexing rules configuration for project files."""

    include: list[str] = Field(
        default_factory=list,
        description="List of glob patterns for files to include in indexing",
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="List of glob patterns for files to exclude from indexing",
    )
    max_file_size: int = Field(
        default=500,
        description="Maximum file size to index in kilobytes",
        ge=1,
    )


class OwnershipRule(BaseModel):
    """Ownership rule mapping code paths to teams and owners."""

    path: str = Field(
        description="Glob pattern matching file paths",
    )
    team: str = Field(
        description="Team name responsible for this path",
    )
    owners: list[str] = Field(
        default_factory=list,
        description="List of owner email addresses or identifiers",
    )


class OwnershipConfig(BaseModel):
    """Ownership mapping configuration."""

    rules: list[OwnershipRule] = Field(
        default_factory=list,
        description="List of ownership rules (first match wins)",
    )


class ProjectSettings(BaseModel):
    """Project-specific analysis and notification settings."""

    enable_static_analysis: bool = Field(
        default=True,
        description="Enable static code analysis",
    )
    enable_security_scanning: bool = Field(
        default=True,
        description="Enable security vulnerability scanning",
    )
    enable_code_quality_checks: bool = Field(
        default=True,
        description="Enable code quality checks",
    )
    notify_on_high_severity: bool = Field(
        default=True,
        description="Send notifications for high severity issues",
    )
    notify_on_medium_severity: bool = Field(
        default=False,
        description="Send notifications for medium severity issues",
    )
    notification_channels: list[str] = Field(
        default_factory=list,
        description="List of notification channels (slack, email, etc.)",
    )
    complexity_threshold: int = Field(
        default=10,
        description="Cyclomatic complexity threshold",
        ge=1,
    )
    duplication_threshold: int = Field(
        default=5,
        description="Code duplication threshold percentage",
        ge=1,
        le=100,
    )


class ProjectConfig(BaseModel):
    """Project-specific configuration.

    This model represents the structure of config/projects/*.yaml files
    and includes all settings for a specific project/repository.
    """

    name: str = Field(
        description="Unique project identifier (used as key in config system)",
    )
    display_name: str = Field(
        description="Human-readable project name",
    )
    description: str = Field(
        default="",
        description="Project description",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this project is enabled for analysis",
    )
    repository: RepositoryConfig = Field(
        description="Repository configuration",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="List of programming languages used in the project",
    )
    indexing: IndexingConfig = Field(
        default_factory=IndexingConfig,
        description="File indexing rules",
    )
    ownership: OwnershipConfig = Field(
        default_factory=OwnershipConfig,
        description="Code ownership mapping",
    )
    settings: ProjectSettings = Field(
        default_factory=ProjectSettings,
        description="Project-specific analysis settings",
    )
