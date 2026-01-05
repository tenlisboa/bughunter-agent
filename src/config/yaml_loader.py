"""YAML configuration loading utilities with environment variable substitution.

This module provides utilities for loading YAML configuration files with support
for environment variable substitution using ${VAR} and ${VAR:-default} syntax.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Regular expression to match ${VAR} or ${VAR:-default} patterns
ENV_VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::(-)?([^}]*))?\}")


def substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in configuration values.

    Supports two syntaxes:
    - ${VAR}: Required environment variable. Raises error if not found.
    - ${VAR:-default}: Optional environment variable with default value.

    The function recursively processes:
    - Strings: Performs variable substitution
    - Dicts: Recursively processes all values
    - Lists: Recursively processes all items
    - Other types: Returns as-is

    Args:
        value: The configuration value to process. Can be a string, dict, list,
               or any other type.

    Returns:
        The processed value with environment variables substituted.

    Raises:
        ValueError: If a required environment variable (${VAR} without default)
                   is not found in the environment.

    Examples:
        >>> os.environ['DB_HOST'] = 'localhost'
        >>> substitute_env_vars('${DB_HOST}')
        'localhost'

        >>> substitute_env_vars('${MISSING_VAR:-default_value}')
        'default_value'

        >>> substitute_env_vars({'db': '${DB_HOST}:5432'})
        {'db': 'localhost:5432'}

        >>> substitute_env_vars(['${DB_HOST}', '${PORT:-8000}'])
        ['localhost', '8000']
    """
    if isinstance(value, str):
        return _substitute_env_vars_in_string(value)
    elif isinstance(value, dict):
        return {key: substitute_env_vars(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [substitute_env_vars(item) for item in value]
    else:
        # Return other types (int, bool, None, etc.) as-is
        return value


def _substitute_env_vars_in_string(text: str) -> str:
    """Substitute environment variables in a single string.

    This is an internal helper function that performs the actual string
    substitution logic for environment variable patterns.

    Args:
        text: The string to process.

    Returns:
        The string with environment variables substituted.

    Raises:
        ValueError: If a required environment variable is not found.
    """
    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        has_default = match.group(2) is not None
        default_value = match.group(3) if has_default else None

        # Try to get the environment variable
        env_value = os.environ.get(var_name)

        if env_value is not None:
            return env_value
        elif has_default:
            # Return default value (empty string if default_value is None)
            return default_value if default_value is not None else ""
        else:
            # Required variable is missing
            raise ValueError(
                f"Required environment variable '{var_name}' is not set. "
                f"Either set the variable or use '${{${var_name}:-default}}' syntax to provide a default value."
            )

    return ENV_VAR_PATTERN.sub(replacer, text)


def load_yaml_with_env_vars(file_path: str) -> dict[str, Any]:
    """Load a YAML file and substitute environment variables.

    This function reads a YAML file, parses it, and recursively substitutes
    all environment variable references in the configuration.

    Args:
        file_path: Path to the YAML file to load.

    Returns:
        The parsed YAML content as a dictionary with environment variables substituted.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If a required environment variable is not found or if
                   the YAML content is invalid.
        yaml.YAMLError: If the YAML file is malformed.

    Examples:
        >>> # Assuming config.yaml contains: database: ${DB_URL:-postgresql://localhost/db}
        >>> config = load_yaml_with_env_vars('config.yaml')
        >>> config['database']
        'postgresql://localhost/db'
    """
    import yaml

    logger.debug(f"Loading YAML configuration from {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            raw_content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML file {file_path}: {e}") from e

    if raw_content is None:
        logger.warning(f"YAML file {file_path} is empty, returning empty dict")
        return {}

    if not isinstance(raw_content, dict):
        raise ValueError(
            f"Expected YAML file {file_path} to contain a mapping (dict), "
            f"but got {type(raw_content).__name__}"
        )

    try:
        result = substitute_env_vars(raw_content)
    except ValueError as e:
        raise ValueError(f"Error in {file_path}: {e}") from e

    # Assert the type for mypy since we know it's a dict at this point
    assert isinstance(result, dict)
    logger.debug(f"Successfully loaded configuration from {file_path}")
    return result


# Singleton cache for global configuration
_global_config_cache: Optional["GlobalConfig"] = None


def load_global_config(config_path: str = "config/global.yaml") -> "GlobalConfig":
    """Load and validate the global configuration from YAML file.

    This function loads the global configuration from the specified YAML file,
    applies environment variable substitution, validates it against the GlobalConfig
    Pydantic model, and caches the result as a singleton.

    The configuration is cached on first load. Subsequent calls return the cached
    instance unless the cache is cleared.

    Args:
        config_path: Path to the global configuration YAML file.
                    Defaults to "config/global.yaml".

    Returns:
        GlobalConfig: The validated global configuration object.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the YAML file is malformed, environment variables are missing,
                   or the configuration fails validation. The error message includes
                   details about what failed validation.

    Examples:
        >>> config = load_global_config()
        >>> print(config.database.url)
        'postgresql://localhost:5432/px_bughunter'

        >>> # With custom path
        >>> config = load_global_config('config/custom.yaml')
    """
    global _global_config_cache

    # Return cached config if available
    if _global_config_cache is not None:
        logger.debug("Returning cached global configuration")
        return _global_config_cache

    # Import here to avoid circular imports
    from pydantic import ValidationError

    from src.config.models import GlobalConfig

    logger.info(f"Loading global configuration from {config_path}")

    # Convert to absolute path if relative
    if not os.path.isabs(config_path):
        config_path = str(Path.cwd() / config_path)

    # Load YAML with environment variable substitution
    try:
        config_data = load_yaml_with_env_vars(config_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load configuration file: {e}")
        raise

    # Validate against GlobalConfig model
    try:
        config = GlobalConfig(**config_data)
    except ValidationError as e:
        error_msg = f"Configuration validation failed for {config_path}:\n"
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            error_msg += f"  - {field}: {error['msg']}\n"
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    # Cache the validated config
    _global_config_cache = config
    logger.info("Global configuration loaded and validated successfully")

    return config


def clear_global_config_cache() -> None:
    """Clear the cached global configuration.

    This function clears the singleton cache for the global configuration,
    forcing the next call to load_global_config() to reload and revalidate
    the configuration file.

    This is primarily useful for testing or when configuration files have
    been updated and need to be reloaded.

    Examples:
        >>> config1 = load_global_config()
        >>> clear_global_config_cache()
        >>> config2 = load_global_config()  # Reloads from file
    """
    global _global_config_cache
    _global_config_cache = None
    logger.debug("Global configuration cache cleared")


# Singleton cache for project configurations
_project_configs_cache: Optional[dict[str, "ProjectConfig"]] = None


def load_project_configs(
    projects_dir: str = "config/projects",
) -> dict[str, "ProjectConfig"]:
    """Load and validate all project configurations from YAML files.

    This function discovers all *.yaml files in the specified projects directory,
    loads each file with environment variable substitution, validates against the
    ProjectConfig Pydantic model, and returns a dictionary mapping project names
    to their configurations.

    The configurations are cached on first load. Subsequent calls return the cached
    dictionary unless the cache is cleared.

    Args:
        projects_dir: Path to the directory containing project YAML files.
                     Defaults to "config/projects".

    Returns:
        dict[str, ProjectConfig]: Dictionary mapping project names to their
                                 validated configuration objects.

    Raises:
        FileNotFoundError: If the projects directory does not exist.
        ValueError: If any YAML file is malformed, environment variables are missing,
                   or a configuration fails validation. The error message includes
                   the filename and details about what failed.

    Examples:
        >>> configs = load_project_configs()
        >>> print(configs['example-project'].repository.url)
        'https://github.com/example/repo.git'

        >>> # With custom path
        >>> configs = load_project_configs('config/custom_projects')
    """
    global _project_configs_cache

    # Return cached configs if available
    if _project_configs_cache is not None:
        logger.debug("Returning cached project configurations")
        return _project_configs_cache

    # Import here to avoid circular imports
    from glob import glob

    from pydantic import ValidationError

    from src.config.models import ProjectConfig

    logger.info(f"Loading project configurations from {projects_dir}")

    # Convert to absolute path if relative
    if not os.path.isabs(projects_dir):
        projects_dir = str(Path.cwd() / projects_dir)

    # Check that the directory exists
    if not os.path.isdir(projects_dir):
        raise FileNotFoundError(f"Projects directory not found: {projects_dir}")

    # Discover all YAML files in the projects directory
    yaml_pattern = os.path.join(projects_dir, "*.yaml")
    yaml_files = glob(yaml_pattern)

    if not yaml_files:
        logger.warning(f"No YAML files found in {projects_dir}")
        _project_configs_cache = {}
        return _project_configs_cache

    logger.info(f"Found {len(yaml_files)} project configuration file(s)")

    # Load and validate each project configuration
    project_configs: dict[str, ProjectConfig] = {}

    for yaml_file in yaml_files:
        filename = os.path.basename(yaml_file)
        logger.debug(f"Loading project configuration from {filename}")

        try:
            # Load YAML with environment variable substitution
            config_data = load_yaml_with_env_vars(yaml_file)

            # Validate against ProjectConfig model
            project_config = ProjectConfig(**config_data)

            # Use the project's name field as the key
            project_name = project_config.name

            # Check for duplicate project names
            if project_name in project_configs:
                raise ValueError(
                    f"Duplicate project name '{project_name}' found in {filename}. "
                    f"Previously defined in another configuration file."
                )

            project_configs[project_name] = project_config
            logger.info(
                f"Successfully loaded project '{project_name}' from {filename}"
            )

        except ValidationError as e:
            error_msg = f"Configuration validation failed for {filename}:\n"
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                error_msg += f"  - {field}: {error['msg']}\n"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

        except (FileNotFoundError, ValueError) as e:
            # Re-raise with filename context if not already included
            if filename not in str(e):
                error_msg = f"Error loading {filename}: {e}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            raise

    # Cache the validated configs
    _project_configs_cache = project_configs
    logger.info(
        f"Successfully loaded {len(project_configs)} project configuration(s)"
    )

    return project_configs


def clear_project_configs_cache() -> None:
    """Clear the cached project configurations.

    This function clears the singleton cache for project configurations,
    forcing the next call to load_project_configs() to reload and revalidate
    all configuration files.

    This is primarily useful for testing or when configuration files have
    been updated and need to be reloaded.

    Examples:
        >>> configs1 = load_project_configs()
        >>> clear_project_configs_cache()
        >>> configs2 = load_project_configs()  # Reloads from files
    """
    global _project_configs_cache
    _project_configs_cache = None
    logger.debug("Project configurations cache cleared")
