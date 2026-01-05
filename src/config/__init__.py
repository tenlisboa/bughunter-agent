"""Configuration management for the application."""

# Legacy settings (environment variables)
from .settings import Settings, settings

# Configuration exceptions
from .exceptions import ConfigurationError

# Configuration models
from .models import (
    AppConfig,
    CORSConfig,
    DatabaseConfig,
    GlobalConfig,
    IndexingConfig,
    LLMConfig,
    LoggingConfig,
    OutputConfig,
    OwnershipConfig,
    OwnershipRule,
    ProjectConfig,
    ProjectSettings,
    RepositoryConfig,
    ServerConfig,
)

# Configuration manager
from .manager import ConfigurationManager, get_config_manager

# YAML loading utilities (for advanced usage)
from .yaml_loader import (
    clear_global_config_cache,
    clear_project_configs_cache,
    load_global_config,
    load_project_configs,
    load_yaml_with_env_vars,
    substitute_env_vars,
)

__all__ = [
    # Legacy settings
    "Settings",
    "settings",
    # Exceptions
    "ConfigurationError",
    # Global config models
    "GlobalConfig",
    "AppConfig",
    "ServerConfig",
    "DatabaseConfig",
    "LLMConfig",
    "OutputConfig",
    "CORSConfig",
    "LoggingConfig",
    # Project config models
    "ProjectConfig",
    "RepositoryConfig",
    "IndexingConfig",
    "OwnershipConfig",
    "OwnershipRule",
    "ProjectSettings",
    # Configuration manager (primary interface)
    "ConfigurationManager",
    "get_config_manager",
    # YAML loading utilities (advanced usage)
    "load_global_config",
    "load_project_configs",
    "load_yaml_with_env_vars",
    "substitute_env_vars",
    "clear_global_config_cache",
    "clear_project_configs_cache",
]
