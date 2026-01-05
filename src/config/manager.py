"""Central configuration manager for accessing global and project configurations.

This module provides a singleton ConfigurationManager that serves as the main
interface for accessing both global and project-specific configurations throughout
the application.
"""

import logging
from typing import Optional

from src.config.models import GlobalConfig, ProjectConfig
from src.config.yaml_loader import (
    clear_global_config_cache,
    clear_project_configs_cache,
    load_global_config,
    load_project_configs,
)

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Central manager for accessing application configurations.

    This class provides a unified interface for accessing both global and
    project-specific configurations. It uses the singleton pattern to ensure
    only one instance exists throughout the application lifecycle.

    The manager delegates to the loading functions in yaml_loader.py, which
    handle caching internally. This provides a cleaner API while maintaining
    the performance benefits of cached configurations.

    Examples:
        >>> # Get the singleton instance
        >>> manager = ConfigurationManager.get_instance()

        >>> # Access global configuration
        >>> global_config = manager.get_global_config()
        >>> print(global_config.database.url)

        >>> # Access a specific project configuration
        >>> project = manager.get_project_config("example-project")
        >>> print(project.repository.url)

        >>> # Get all projects
        >>> all_projects = manager.get_all_projects()
        >>> for name, config in all_projects.items():
        ...     print(f"{name}: {config.display_name}")

        >>> # Reload configurations after file changes
        >>> manager.reload()
    """

    _instance: Optional["ConfigurationManager"] = None

    def __init__(
        self,
        global_config_path: str = "config/global.yaml",
        projects_dir: str = "config/projects",
    ) -> None:
        """Initialize the ConfigurationManager.

        Note: Use get_instance() instead of directly instantiating this class
        to ensure singleton behavior.

        Args:
            global_config_path: Path to the global configuration YAML file.
                              Defaults to "config/global.yaml".
            projects_dir: Path to the directory containing project YAML files.
                        Defaults to "config/projects".
        """
        self._global_config_path = global_config_path
        self._projects_dir = projects_dir
        logger.debug(
            f"ConfigurationManager initialized with global_config_path={global_config_path}, "
            f"projects_dir={projects_dir}"
        )

    @classmethod
    def get_instance(
        cls,
        global_config_path: str = "config/global.yaml",
        projects_dir: str = "config/projects",
    ) -> "ConfigurationManager":
        """Get or create the singleton ConfigurationManager instance.

        This method ensures only one ConfigurationManager instance exists.
        Subsequent calls return the same instance, ignoring any path parameters
        passed after the first call.

        Args:
            global_config_path: Path to the global configuration YAML file.
                              Only used on first call. Defaults to "config/global.yaml".
            projects_dir: Path to the directory containing project YAML files.
                        Only used on first call. Defaults to "config/projects".

        Returns:
            ConfigurationManager: The singleton instance.

        Examples:
            >>> manager1 = ConfigurationManager.get_instance()
            >>> manager2 = ConfigurationManager.get_instance()
            >>> assert manager1 is manager2  # Same instance
        """
        if cls._instance is None:
            logger.info("Creating new ConfigurationManager singleton instance")
            cls._instance = cls(
                global_config_path=global_config_path,
                projects_dir=projects_dir,
            )
        else:
            logger.debug("Returning existing ConfigurationManager instance")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        This method is primarily useful for testing when you need to create
        a fresh ConfigurationManager instance with different parameters.

        Examples:
            >>> ConfigurationManager.reset_instance()
            >>> manager = ConfigurationManager.get_instance("config/test.yaml")
        """
        cls._instance = None
        logger.debug("ConfigurationManager instance reset")

    def get_global_config(self) -> GlobalConfig:
        """Get the global application configuration.

        This method loads and validates the global configuration from the
        configured YAML file. The result is cached internally by the
        yaml_loader module for performance.

        Returns:
            GlobalConfig: The validated global configuration object.

        Raises:
            FileNotFoundError: If the global configuration file does not exist.
            ValueError: If the configuration is invalid or environment variables
                       are missing.

        Examples:
            >>> manager = ConfigurationManager.get_instance()
            >>> config = manager.get_global_config()
            >>> print(config.database.url)
            'postgresql://localhost:5432/px_bughunter'
        """
        logger.debug(f"Loading global config from {self._global_config_path}")
        return load_global_config(self._global_config_path)

    def get_project_config(self, project_name: str) -> ProjectConfig:
        """Get the configuration for a specific project.

        Args:
            project_name: The unique name/identifier of the project.

        Returns:
            ProjectConfig: The validated project configuration object.

        Raises:
            KeyError: If no project with the given name exists.
            FileNotFoundError: If the projects directory does not exist.
            ValueError: If any project configuration is invalid.

        Examples:
            >>> manager = ConfigurationManager.get_instance()
            >>> project = manager.get_project_config("example-project")
            >>> print(project.repository.url)
            'https://github.com/example/repo.git'
        """
        logger.debug(f"Loading project config for '{project_name}'")
        projects = load_project_configs(self._projects_dir)

        if project_name not in projects:
            available = ", ".join(projects.keys()) if projects else "none"
            error_msg = (
                f"Project '{project_name}' not found. "
                f"Available projects: {available}"
            )
            logger.error(error_msg)
            raise KeyError(error_msg)

        return projects[project_name]

    def get_all_projects(self) -> dict[str, ProjectConfig]:
        """Get all project configurations.

        Returns:
            dict[str, ProjectConfig]: Dictionary mapping project names to their
                                     validated configuration objects.

        Raises:
            FileNotFoundError: If the projects directory does not exist.
            ValueError: If any project configuration is invalid.

        Examples:
            >>> manager = ConfigurationManager.get_instance()
            >>> projects = manager.get_all_projects()
            >>> for name, config in projects.items():
            ...     print(f"{name}: {config.display_name}")
            'example-project: Example Project'
        """
        logger.debug(f"Loading all project configs from {self._projects_dir}")
        return load_project_configs(self._projects_dir)

    def reload(self) -> None:
        """Reload all configurations from disk.

        This method clears all internal caches and forces a fresh load of both
        global and project configurations on the next access. This is useful
        when configuration files have been updated and need to be reloaded
        without restarting the application.

        Note: This provides hot-reload capability for configuration changes.

        Examples:
            >>> manager = ConfigurationManager.get_instance()
            >>> # ... configuration files are updated ...
            >>> manager.reload()
            >>> # Next access will load fresh configs
            >>> config = manager.get_global_config()
        """
        logger.info("Reloading all configurations")
        clear_global_config_cache()
        clear_project_configs_cache()
        logger.info("Configuration caches cleared, next access will reload from disk")


def get_config_manager(
    global_config_path: str = "config/global.yaml",
    projects_dir: str = "config/projects",
) -> ConfigurationManager:
    """Get the singleton ConfigurationManager instance.

    This is a convenience function that provides a simpler way to access
    the ConfigurationManager without needing to call get_instance() directly.

    Args:
        global_config_path: Path to the global configuration YAML file.
                          Only used on first call. Defaults to "config/global.yaml".
        projects_dir: Path to the directory containing project YAML files.
                    Only used on first call. Defaults to "config/projects".

    Returns:
        ConfigurationManager: The singleton instance.

    Examples:
        >>> from src.config.manager import get_config_manager
        >>> manager = get_config_manager()
        >>> config = manager.get_global_config()
    """
    return ConfigurationManager.get_instance(
        global_config_path=global_config_path,
        projects_dir=projects_dir,
    )
